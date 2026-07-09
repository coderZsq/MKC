import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http_parser/http_parser.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/config/env.dart';
import 'package:mkc_client/data/datasources/secure/secure_token_storage.dart';
import 'package:mkc_client/domain/entities/picked_file.dart';
import 'package:mkc_client/domain/services/file_picker_service.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';
import 'package:mkc_client/presentation/routes/app_routes.dart';

/// S2 全链路 E2E 测试：Upload -> TaskCenter -> TaskDetail -> Result/Retry/ContentView。
///
/// 本测试不依赖 AI Service 真实推理或 Gateway 内部 Key。它通过直接调用 Gateway
/// 公开 API 与 Flutter Web 集成测试，覆盖 S2 流水线中可在本地 Gateway 上稳定复现的
/// P0/P1 场景（任务创建、状态展示、结果/重试权限与错误、内容查看错误态）。
///
/// 运行前请确保：
/// - Gateway 已启动并监听 8080（BASE_URL 指向 localhost:8080/api/v1）。
/// - MySQL / Redis / MinIO 已可访问。
/// - chromedriver 在 4444 端口运行。
///
/// 执行命令：
/// flutter drive --driver=test_driver/integration_test.dart \
///   --target=integration_test/s2_pipeline_e2e_test.dart -d chrome \
///   --dart-define=BASE_URL=http://localhost:8080/api/v1 \
///   --dart-define=STORAGE_HOST=localhost
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final storage = SecureTokenStorage();
  const baseUrl = Env.baseUrl;

  String uniqueEmail(String suffix) {
    return 'e2e_${DateTime.now().millisecondsSinceEpoch}_$suffix@example.com';
  }

  /// Minimal MP3-like bytes that pass Go's http.DetectContentType as audio/mpeg.
  Uint8List makeMp3Bytes(int size) {
    final bytes = Uint8List(size);
    bytes[0] = 0xFF;
    bytes[1] = 0xFB;
    bytes[2] = 0x90;
    bytes[3] = 0x00;
    for (var i = 4; i < size; i++) {
      bytes[i] = i % 256;
    }
    return bytes;
  }

  /// Minimal valid PDF bytes that pass Go's http.DetectContentType.
  Uint8List makePdfBytes(int size) {
    final bytes = Uint8List(size);
    const header = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n';
    final headerBytes = utf8.encode(header);
    bytes.setRange(0, headerBytes.length, headerBytes);
    for (var i = headerBytes.length; i < size; i++) {
      bytes[i] = i % 256;
    }
    return bytes;
  }

  Uint8List makeTextBytes(String content) => Uint8List.fromList(utf8.encode(content));

  Future<Map<String, dynamic>> registerUser(String email, String password) async {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        validateStatus: (_) => true,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ),
    );
    final response = await dio.post<Map<String, dynamic>>(
      '/auth/register',
      data: {'email': email, 'password': password, 'nickname': 'E2E'},
    );
    final body = response.data!;
    if (body['success'] != true) {
      throw Exception('Failed to register user: ${body['error']}');
    }
    return body['data'] as Map<String, dynamic>;
  }

  Dio authenticatedDio(String accessToken) {
    return Dio(
      BaseOptions(
        baseUrl: baseUrl,
        headers: {'Authorization': 'Bearer $accessToken'},
        validateStatus: (_) => true,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 30),
      ),
    );
  }

  Future<Map<String, dynamic>> uploadFile({
    required String accessToken,
    required Uint8List bytes,
    required String filename,
    required String mimeType,
  }) async {
    final dio = authenticatedDio(accessToken);
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/files/upload',
      data: formData,
    );
    final body = response.data!;
    if (body['success'] != true) {
      throw Exception('Upload failed: ${body['error']}');
    }
    return body['data'] as Map<String, dynamic>;
  }

  Future<void> pumpUntilFound(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(const Duration(milliseconds: 200));
      if (finder.evaluate().isNotEmpty) return;
    }
    throw Exception('Timed out waiting for $finder');
  }

  Future<void> pumpUntilPage(WidgetTester tester, String title) async {
    await pumpUntilFound(tester, find.text(title));
    await tester.pumpAndSettle();
  }

  GoRouter currentRouter(WidgetTester tester) {
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    return app.routerConfig as GoRouter;
  }

  late Map<String, dynamic> testUser;

  Future<void> restoreAuth(Map<String, dynamic> user) async {
    await storage.setTokens(
      accessToken: user['access_token'] as String,
      refreshToken: user['refresh_token'] as String,
    );
  }

  setUpAll(() async {
    testUser = await registerUser(uniqueEmail('s2_shared'), 'Password123!');
    await storage.setTokens(
      accessToken: testUser['access_token'] as String,
      refreshToken: testUser['refresh_token'] as String,
    );
  });

  setUp(() async {
    await storage.clearTokens();
  });

  group('Direct API assertions', () {
    testWidgets('upload MP3 creates a media_parse task', (tester) async {
      final data = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeMp3Bytes(1024),
        filename: 's2_asr.mp3',
        mimeType: 'audio/mpeg',
      );

      expect(data['resource_id'], isNotEmpty);
      expect(data['task_id'], isNotEmpty);
      expect(data['type'], 'media_parse');
      expect(data['mime_type'], 'audio/mpeg');
      expect(data['size_bytes'], 1024);
    });

    testWidgets('upload PDF creates a pdf_parse task', (tester) async {
      final data = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makePdfBytes(2048),
        filename: 's2_extract.pdf',
        mimeType: 'application/pdf',
      );

      expect(data['type'], 'pdf_parse');
      expect(data['mime_type'], 'application/pdf');
    });

    testWidgets('result endpoint returns TASK_NOT_COMPLETED for pending media task', (
      tester,
    ) async {
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeMp3Bytes(1024),
        filename: 's2_result_pending.mp3',
        mimeType: 'audio/mpeg',
      );
      final taskId = upload['task_id'] as String;
      final dio = authenticatedDio(testUser['access_token'] as String);

      final response = await dio.get<Map<String, dynamic>>('/tasks/$taskId/result');

      expect(response.statusCode, 400);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'TASK_NOT_COMPLETED');
    });

    testWidgets('result endpoint returns 404 for another users task', (tester) async {
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeMp3Bytes(1024),
        filename: 's2_result_owner.mp3',
        mimeType: 'audio/mpeg',
      );
      final taskId = upload['task_id'] as String;

      final otherUser = await registerUser(uniqueEmail('s2_other'), 'Password123!');
      final dio = authenticatedDio(otherUser['access_token'] as String);

      final response = await dio.get<Map<String, dynamic>>('/tasks/$taskId/result');

      expect(response.statusCode, 404);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'NOT_FOUND');
    });

    testWidgets('result endpoint returns 401 without token', (tester) async {
      final dio = Dio(BaseOptions(baseUrl: baseUrl, validateStatus: (_) => true));

      final response = await dio.get<Map<String, dynamic>>(
        '/tasks/00000000-0000-0000-0000-000000000000/result',
      );

      expect(response.statusCode, 401);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'AUTH_INVALID_TOKEN');
    });

    testWidgets('retry returns TASK_NOT_RETRYABLE for pending document task', (
      tester,
    ) async {
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeTextBytes('S2 retry test document.'),
        filename: 's2_retry_doc.txt',
        mimeType: 'text/plain',
      );
      final taskId = upload['task_id'] as String;
      final dio = authenticatedDio(testUser['access_token'] as String);

      final response = await dio.post<Map<String, dynamic>>('/tasks/$taskId/retry');

      expect(response.statusCode, 400);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'TASK_NOT_RETRYABLE');
    });

    testWidgets('retry returns 404 for non-existent task', (tester) async {
      final dio = authenticatedDio(testUser['access_token'] as String);

      final response = await dio.post<Map<String, dynamic>>(
        '/tasks/00000000-0000-0000-0000-000000000000/retry',
      );

      expect(response.statusCode, 404);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'NOT_FOUND');
    });

    testWidgets('retry returns 404 when caller does not own the task', (tester) async {
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeTextBytes('S2 cross-user retry test.'),
        filename: 's2_retry_owner.txt',
        mimeType: 'text/plain',
      );
      final taskId = upload['task_id'] as String;

      final otherUser = await registerUser(uniqueEmail('s2_retry_other'), 'Password123!');
      final dio = authenticatedDio(otherUser['access_token'] as String);

      final response = await dio.post<Map<String, dynamic>>('/tasks/$taskId/retry');

      expect(response.statusCode, 404);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'NOT_FOUND');
    });

    testWidgets('retry returns 401 without token', (tester) async {
      final dio = Dio(BaseOptions(baseUrl: baseUrl, validateStatus: (_) => true));

      final response = await dio.post<Map<String, dynamic>>(
        '/tasks/00000000-0000-0000-0000-000000000000/retry',
      );

      expect(response.statusCode, 401);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'AUTH_INVALID_TOKEN');
    });
  });

  Finder cardFor(String filename) => find.ancestor(
        of: find.text(filename),
        matching: find.byType(Card),
      );

  group('UI E2E on Chrome', () {
    testWidgets('redirects unauthenticated user to login', (tester) async {
      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '登录 MKC');
      expect(find.widgetWithText(ElevatedButton, '登录'), findsOneWidget);
    });

    testWidgets('uploads MP3 and shows pending media_parse task in task center', (
      tester,
    ) async {
      await restoreAuth(testUser);
      final filename = 's2_ui_asr_${DateTime.now().millisecondsSinceEpoch}.mp3';

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [
          filePickerServiceProvider.overrideWithValue(
            FakeFilePickerService()
              ..nextFile = PickedFile(
                bytes: makeMp3Bytes(1024),
                name: filename,
                size: 1024,
                extension: 'mp3',
              ),
          ),
        ],
        child: const MKCApp(),
      );

      await tester.pumpWidget(app);
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      await tester.tap(find.text('上传文件'));
      await pumpUntilPage(tester, '上传文件');

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('开始上传'));

      await tester.tap(find.text('开始上传'));
      await pumpUntilFound(tester, find.text('上传成功'));

      await tester.tap(find.text('查看任务中心'));
      await pumpUntilPage(tester, '任务中心');

      await pumpUntilFound(tester, find.text(filename));
      final card = cardFor(filename);
      expect(find.descendant(of: card, matching: find.text(filename)), findsOneWidget);
      expect(find.descendant(of: card, matching: find.text('音视频解析')), findsOneWidget);
      expect(find.descendant(of: card, matching: find.text('等待中')), findsOneWidget);
      expect(find.text('查看内容'), findsNothing);
    });

    testWidgets('uploads PDF and shows pending pdf_parse task in task center', (
      tester,
    ) async {
      await restoreAuth(testUser);
      final filename = 's2_ui_pdf_${DateTime.now().millisecondsSinceEpoch}.pdf';

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [
          filePickerServiceProvider.overrideWithValue(
            FakeFilePickerService()
              ..nextFile = PickedFile(
                bytes: makePdfBytes(2048),
                name: filename,
                size: 2048,
                extension: 'pdf',
              ),
          ),
        ],
        child: const MKCApp(),
      );

      await tester.pumpWidget(app);
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      await tester.tap(find.text('上传文件'));
      await pumpUntilPage(tester, '上传文件');

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('开始上传'));

      await tester.tap(find.text('开始上传'));
      await pumpUntilFound(tester, find.text('上传成功'));

      await tester.tap(find.text('查看任务中心'));
      await pumpUntilPage(tester, '任务中心');

      await pumpUntilFound(tester, find.text(filename));
      final card = cardFor(filename);
      expect(find.descendant(of: card, matching: find.text(filename)), findsOneWidget);
      expect(find.descendant(of: card, matching: find.text('PDF 解析')), findsOneWidget);
      expect(find.descendant(of: card, matching: find.text('等待中')), findsOneWidget);
      expect(find.text('查看内容'), findsNothing);
    });

    testWidgets('tap task navigates to detail showing pending status and progress', (
      tester,
    ) async {
      await restoreAuth(testUser);
      final filename = 's2_ui_detail_${DateTime.now().millisecondsSinceEpoch}.mp3';
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeMp3Bytes(1024),
        filename: filename,
        mimeType: 'audio/mpeg',
      );
      final resourceName = upload['name'] as String;

      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(taskCenterRoute);
      await pumpUntilPage(tester, '任务中心');

      await pumpUntilFound(tester, find.text(resourceName));
      await tester.tap(find.text(resourceName));
      await pumpUntilPage(tester, '任务详情');

      expect(find.text(resourceName), findsOneWidget);
      expect(find.text('等待中'), findsOneWidget);
      expect(find.text('进度: 0%'), findsOneWidget);
    });

    testWidgets('content view for pending audio task shows not-completed message', (
      tester,
    ) async {
      await restoreAuth(testUser);
      final filename = 's2_ui_content_audio_${DateTime.now().millisecondsSinceEpoch}.mp3';
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makeMp3Bytes(1024),
        filename: filename,
        mimeType: 'audio/mpeg',
      );
      final taskId = upload['task_id'] as String;

      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go('/tasks/$taskId/content?type=audio');
      await pumpUntilFound(tester, find.text('处理中，请稍后'));

      expect(find.text('处理中，请稍后'), findsOneWidget);
      expect(find.text('刷新'), findsOneWidget);
    });

    testWidgets('content view for pending PDF task shows not-completed message', (
      tester,
    ) async {
      await restoreAuth(testUser);
      final filename = 's2_ui_content_pdf_${DateTime.now().millisecondsSinceEpoch}.pdf';
      final upload = await uploadFile(
        accessToken: testUser['access_token'] as String,
        bytes: makePdfBytes(2048),
        filename: filename,
        mimeType: 'application/pdf',
      );
      final taskId = upload['task_id'] as String;

      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go('/tasks/$taskId/content?type=pdf');
      await pumpUntilFound(tester, find.text('处理中，请稍后'));

      expect(find.text('处理中，请稍后'), findsOneWidget);
      expect(find.text('刷新'), findsOneWidget);
    });
  });
}

class FakeFilePickerService implements FilePickerService {
  PickedFile? nextFile;

  @override
  Future<PickedFile?> pickSingleFile() async => nextFile;
}
