import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/upload_response_model.dart';
import 'package:mkc_client/presentation/pages/upload_page.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/upload_test_helpers.dart';

void main() {
  group('UploadPage', () {
    testWidgets('renders select file button', (WidgetTester tester) async {
      await _pumpPage(tester);
      expect(find.text('选择文件'), findsOneWidget);
    });

    testWidgets('selecting unsupported file shows error message', (
      WidgetTester tester,
    ) async {
      final picker = FakeFilePickerService();
      picker.nextFile = fakeFile(size: 1024, extension: 'exe');

      await _pumpPage(tester, picker: picker);
      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();

      expect(find.text('不支持的文件类型'), findsOneWidget);
    });

    testWidgets('selecting oversized file shows size limit message', (
      WidgetTester tester,
    ) async {
      final picker = FakeFilePickerService();
      picker.nextFile = fakeFile(size: 501 * 1024 * 1024, extension: 'mp3');

      await _pumpPage(tester, picker: picker);
      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();

      expect(find.text('文件超过当前平台大小限制'), findsOneWidget);
    });

    testWidgets('successful upload shows task id and task center link', (
      WidgetTester tester,
    ) async {
      final picker = FakeFilePickerService();
      final repository = FakeFileRepository();
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      repository.nextResult = const Result.success(
        UploadResponseModel(
          resourceId: 'res-1',
          taskId: 'task-abc',
          name: 'test.mp3',
          type: 'audio',
          status: 'pending',
          sizeBytes: 1024,
          mimeType: 'audio/mpeg',
          createdAt: 1700000000,
        ),
      );

      await _pumpPage(tester, picker: picker, repository: repository);
      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('开始上传'));
      await tester.pumpAndSettle();

      expect(find.text('上传成功'), findsOneWidget);
      expect(find.text('任务 ID: task-abc'), findsOneWidget);
      expect(find.text('查看任务中心'), findsOneWidget);
    });

    testWidgets('network error shows network message', (WidgetTester tester) async {
      final picker = FakeFilePickerService();
      final repository = FakeFileRepository();
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      repository.nextResult = const Result.failure(NetworkException());

      await _pumpPage(tester, picker: picker, repository: repository);
      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('开始上传'));
      await tester.pumpAndSettle();

      expect(find.text('网络异常，请检查连接'), findsOneWidget);
    });

    testWidgets('server 413 error shows file too large message', (
      WidgetTester tester,
    ) async {
      final picker = FakeFilePickerService();
      final repository = FakeFileRepository();
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      repository.nextResult = const Result.failure(
        ServerException(code: '413'),
      );

      await _pumpPage(tester, picker: picker, repository: repository);
      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('开始上传'));
      await tester.pumpAndSettle();

      expect(find.text('文件过大，请重新选择'), findsOneWidget);
    });
  });
}

Future<void> _pumpPage(
  WidgetTester tester, {
  FakeFilePickerService? picker,
  FakeFileRepository? repository,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        if (picker != null)
          filePickerServiceProvider.overrideWithValue(picker),
        if (repository != null)
          fileRepositoryProvider.overrideWithValue(repository),
      ],
      child: const MaterialApp(home: UploadPage()),
    ),
  );
  await tester.pumpAndSettle();
}
