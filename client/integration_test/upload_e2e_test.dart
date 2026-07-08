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
import 'package:mkc_client/data/models/upload_response_model.dart';
import 'package:mkc_client/data/repositories/file_repository.dart';
import 'package:mkc_client/domain/entities/picked_file.dart';
import 'package:mkc_client/domain/services/file_picker_service.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

/// E2E tests for S1-3 file upload API and S1-4 Flutter upload page.
///
/// Runs in Chrome against a live Gateway. Before running, ensure:
/// - MySQL / Redis / MinIO are available (via K8s port-forward or local).
/// - Gateway is listening on the BASE_URL host (default localhost:8080).
/// - chromedriver is running on port 4444.
///
/// Command:
/// flutter drive --driver=test_driver/integration_test.dart \
///   --target=integration_test/upload_e2e_test.dart -d chrome \
///   --dart-define=BASE_URL=http://localhost:8080/api/v1
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final storage = SecureTokenStorage();
  const baseUrl = Env.baseUrl;

  late Map<String, dynamic> testUser;

  String uniqueEmail(String suffix) {
    return 'e2e_${DateTime.now().millisecondsSinceEpoch}_$suffix@example.com';
  }

  /// Minimal MP3-like bytes that pass Go's http.DetectContentType as audio/mpeg.
  Uint8List makeMp3Bytes(int size) {
    final bytes = Uint8List(size);
    // MPEG audio frame sync bytes.
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
    String password, {
    bool storeToken = false,
  }) async {
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
    if (storeToken) {
      final data = body['data'] as Map<String, dynamic>;
      await storage.setTokens(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
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

  Future<void> navigateToUploadPage(WidgetTester tester, {required Widget app}) async {
    await tester.pumpWidget(app);
    await pumpUntilPage(tester, '首页占位 — 功能开发中');
    await tester.tap(find.text('上传文件'));
    await pumpUntilPage(tester, '上传文件');
  }

  setUpAll(() async {
    testUser = await registerUser(uniqueEmail('shared'), 'Password123!', storeToken: true);
  });

  group('S1-3 upload API direct assertions', () {
    testWidgets('returns 401 without token', (tester) async {
      await storage.clearTokens();
      final dio = Dio(
        BaseOptions(baseUrl: baseUrl, validateStatus: (_) => true),
      );
      final response = await dio.post<Map<String, dynamic>>(
        '/files/upload',
        data: FormData.fromMap({}),
      );

      expect(response.statusCode, 401);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'AUTH_INVALID_TOKEN');
    });

    testWidgets('returns 400 when file field is missing', (tester) async {
      final dio = authenticatedDio(testUser['access_token'] as String);

      final response = await dio.post<Map<String, dynamic>>(
        '/files/upload',
        data: FormData.fromMap({}),
      );

      expect(response.statusCode, 400);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'FILE_MISSING');
    });

    testWidgets('returns 415 for unsupported file type', (tester) async {
      final dio = authenticatedDio(testUser['access_token'] as String);

      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0]),
          filename: 'test.jpg',
        ),
      });

      final response = await dio.post<Map<String, dynamic>>(
        '/files/upload',
        data: formData,
      );

      expect(response.statusCode, 415);
      final error = response.data!['error'] as Map<String, dynamic>;
      expect(error['code'], 'FILE_UNSUPPORTED_TYPE');
    });

    testWidgets('returns 200 with resource and media_parse task for MP3', (
      tester,
    ) async {
      final dio = authenticatedDio(testUser['access_token'] as String);

      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          makeMp3Bytes(1024),
          filename: 'test.mp3',
          contentType: MediaType.parse('audio/mpeg'),
        ),
      });

      final response = await dio.post<Map<String, dynamic>>(
        '/files/upload',
        data: formData,
      );

      expect(response.statusCode, 200);
      final data = response.data!['data'] as Map<String, dynamic>;
      expect(data['resource_id'], isNotEmpty);
      expect(data['task_id'], isNotEmpty);
      expect(data['type'], 'media_parse');
      expect(data['mime_type'], 'audio/mpeg');
      expect(data['size_bytes'], 1024);
    });
  });

  group('S1-4 upload page E2E on Chrome', () {
    Future<void> restoreAuth() async {
      await storage.setTokens(
        accessToken: testUser['access_token'] as String,
        refreshToken: testUser['refresh_token'] as String,
      );
    }

    testWidgets('redirects unauthenticated user to login', (tester) async {
      await storage.clearTokens();
      await tester.pumpWidget(ProviderScope(key: UniqueKey(), child: const MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      expect(find.widgetWithText(ElevatedButton, '登录'), findsOneWidget);
    });

    testWidgets('shows local size limit error for oversized file', (tester) async {
      await restoreAuth();

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [filePickerServiceProvider.overrideWithValue(FakeFilePickerService()
          ..nextFile = PickedFile(
            bytes: Uint8List(0),
            name: 'big.mp3',
            size: 150 * 1024 * 1024, // exceeds Web 100 MB limit
            extension: 'mp3',
          ))],
        child: const MKCApp(),
      );

      await navigateToUploadPage(tester, app: app);

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('文件超过当前平台大小限制'));

      expect(find.text('文件超过当前平台大小限制'), findsOneWidget);
    });

    testWidgets('shows unsupported type error for bad extension', (tester) async {
      await restoreAuth();

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [filePickerServiceProvider.overrideWithValue(FakeFilePickerService()
          ..nextFile = PickedFile(
            bytes: Uint8List(4),
            name: 'malware.exe',
            size: 1024,
            extension: 'exe',
          ))],
        child: const MKCApp(),
      );

      await navigateToUploadPage(tester, app: app);

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('不支持的文件类型'));

      expect(find.text('不支持的文件类型'), findsOneWidget);
    });

    testWidgets('uploads a valid MP3 and navigates to task center', (tester) async {
      await restoreAuth();

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [filePickerServiceProvider.overrideWithValue(FakeFilePickerService()
          ..nextFile = PickedFile(
            bytes: makeMp3Bytes(1024),
            name: 'sample.mp3',
            size: 1024,
            extension: 'mp3',
          ))],
        child: const MKCApp(),
      );

      await navigateToUploadPage(tester, app: app);

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('开始上传'));

      await tester.tap(find.text('开始上传'));
      await pumpUntilFound(tester, find.text('上传成功'));

      expect(find.text('上传成功'), findsOneWidget);
      expect(find.textContaining('任务 ID:'), findsOneWidget);

      await tester.tap(find.text('查看任务中心'));
      await pumpUntilPage(tester, '任务中心');
    });

    testWidgets('shows server file-too-large message when API returns 413', (
      tester,
    ) async {
      await restoreAuth();

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [
          filePickerServiceProvider.overrideWithValue(FakeFilePickerService()
            ..nextFile = PickedFile(
              bytes: makeMp3Bytes(1024),
              name: 'sample.mp3',
              size: 1024,
              extension: 'mp3',
            )),
          fileRepositoryProvider.overrideWithValue(FakeFileRepository()
            ..nextResult = const Result.failure(
              ServerException(code: 'FILE_TOO_LARGE'),
            )),
        ],
        child: const MKCApp(),
      );

      await navigateToUploadPage(tester, app: app);

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('开始上传'));

      await tester.tap(find.text('开始上传'));
      await pumpUntilFound(tester, find.text('文件过大，请重新选择'));

      expect(find.text('文件过大，请重新选择'), findsOneWidget);
    });

    testWidgets('shows server unsupported-type message when API returns 415', (
      tester,
    ) async {
      await restoreAuth();

      final app = ProviderScope(
        key: UniqueKey(),
        overrides: [
          filePickerServiceProvider.overrideWithValue(FakeFilePickerService()
            ..nextFile = PickedFile(
              bytes: makeMp3Bytes(1024),
              name: 'sample.mp3',
              size: 1024,
              extension: 'mp3',
            )),
          fileRepositoryProvider.overrideWithValue(FakeFileRepository()
            ..nextResult = const Result.failure(
              ServerException(code: 'FILE_UNSUPPORTED_TYPE'),
            )),
        ],
        child: const MKCApp(),
      );

      await navigateToUploadPage(tester, app: app);

      await tester.tap(find.text('选择文件'));
      await pumpUntilFound(tester, find.text('开始上传'));

      await tester.tap(find.text('开始上传'));
      await pumpUntilFound(tester, find.text('服务器不支持该文件类型'));

      expect(find.text('服务器不支持该文件类型'), findsOneWidget);
    });
  });
}

class FakeFilePickerService implements FilePickerService {
  PickedFile? nextFile;

  @override
  Future<PickedFile?> pickSingleFile() async => nextFile;
}

class FakeFileRepository implements FileRepository {
  Result<UploadResponseModel>? nextResult;

  @override
  Future<Result<UploadResponseModel>> uploadFile({
    required PickedFile file,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) async {
    onProgress(50, 100);
    onProgress(100, 100);
    return nextResult ??
        const Result.success(
          UploadResponseModel(
            resourceId: 'res-e2e',
            taskId: 'task-e2e',
            name: 'sample.mp3',
            type: 'media_parse',
            status: 'pending',
            sizeBytes: 1024,
            mimeType: 'audio/mpeg',
            createdAt: 1700000000,
          ),
        );
  }
}
