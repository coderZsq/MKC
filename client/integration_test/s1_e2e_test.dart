import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http_parser/http_parser.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/config/env.dart';
import 'package:mkc_client/data/datasources/secure/secure_token_storage.dart';
import 'package:mkc_client/domain/entities/picked_file.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/domain/services/file_picker_service.dart';
import 'package:mkc_client/presentation/providers/app_provider.dart';
import 'package:mkc_client/presentation/providers/task_sse_provider.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';

/// S1 全链路 E2E 测试：Auth → Upload → TaskCenter → TaskDetail → SSE。
///
/// 运行前请确保：
/// - Gateway 已启动并监听 8080（BASE_URL 指向 localhost:8080/api/v1）。
/// - MySQL / Redis / MinIO 已可访问。
/// - chromedriver 在 4444 端口运行。
///
/// 执行命令：
/// flutter drive --driver=test_driver/integration_test.dart \
///   --target=integration_test/s1_e2e_test.dart -d chrome \
///   --dart-define=BASE_URL=http://localhost:8080/api/v1
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

  Future<Map<String, dynamic>> registerUser(
    String email,
    String password,
  ) async {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        validateStatus: (_) => true,
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
      ),
    );
  }

  Future<String> uploadMp3AndReturnTaskId(String accessToken) async {
    final dio = authenticatedDio(accessToken);
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        makeMp3Bytes(1024),
        filename: 'sample.mp3',
        contentType: MediaType.parse('audio/mpeg'),
      ),
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/files/upload',
      data: formData,
    );
    final body = response.data!;
    if (body['success'] != true) {
      throw Exception('Failed to upload file: ${body['error']}');
    }
    final data = body['data'] as Map<String, dynamic>;
    return data['task_id'] as String;
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

  Finder submitButton(String text) => find.widgetWithText(ElevatedButton, text);

  Future<void> enterEmail(WidgetTester tester, String email) async {
    await tester.enterText(find.widgetWithText(TextFormField, '邮箱'), email);
  }

  Future<void> enterPassword(WidgetTester tester, String password) async {
    await tester.enterText(find.widgetWithText(TextFormField, '密码'), password);
  }

  setUp(() async {
    await storage.clearTokens();
  });

  group('S1 full-link E2E on Chrome', () {
    testWidgets('registers, uploads, and navigates to task center and detail', (
      WidgetTester tester,
    ) async {
      const password = 'Password123';
      final email = uniqueEmail('s1');

      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');

      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');

      await enterEmail(tester, email);
      await tester.enterText(
        find.widgetWithText(TextFormField, '昵称（可选）'),
        'E2E User',
      );
      await enterPassword(tester, password);
      await tester.enterText(
        find.widgetWithText(TextFormField, '确认密码'),
        password,
      );
      await tester.tap(submitButton('注册'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [
          filePickerServiceProvider.overrideWithValue(
            FakeFilePickerService()
              ..nextFile = PickedFile(
                bytes: makeMp3Bytes(1024),
                name: 'sample.mp3',
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

      expect(find.textContaining('任务 ID:'), findsOneWidget);

      await tester.tap(find.text('查看任务中心'));
      await pumpUntilPage(tester, '任务中心');

      await pumpUntilFound(tester, find.text('sample.mp3'));
      expect(find.text('等待中'), findsWidgets);
      expect(find.text('0%'), findsWidgets);

      await tester.tap(find.text('sample.mp3'));
      await pumpUntilPage(tester, '任务详情');

      expect(find.text('sample.mp3'), findsOneWidget);
      expect(find.text('等待中'), findsOneWidget);
      expect(find.text('进度: 0%'), findsOneWidget);
    });

    testWidgets('SSE endpoint delivers initial status event for a task', (
      WidgetTester tester,
    ) async {
      final user = await registerUser(uniqueEmail('sse'), 'Password123');
      final accessToken = user['access_token'] as String;
      final taskId = await uploadMp3AndReturnTaskId(accessToken);

      final container = ProviderContainer(
        overrides: [
          tokenProvider.overrideWithValue(
            FakeTokenProvider(accessToken),
          ),
        ],
      );
      addTearDown(container.dispose);

      final provider = taskEventStreamProvider(taskId);
      final sub = container.listen(provider, (_, __) {});
      addTearDown(sub.close);

      final event = await container.read(provider.future).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw Exception('Timed out waiting for SSE event'),
      );

      expect(event, isNotNull);
      expect(event!.taskId, taskId);
      expect(event.status, 'pending');
      expect(event.progress, 0);
    });
  });
}

class FakeFilePickerService implements FilePickerService {
  PickedFile? nextFile;

  @override
  Future<PickedFile?> pickSingleFile() async => nextFile;
}

class FakeTokenProvider implements TokenProvider {
  const FakeTokenProvider(this.accessToken);

  final String accessToken;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {}
}
