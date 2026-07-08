import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/upload_response_model.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/upload_test_helpers.dart';

void main() {
  late FakeFilePickerService picker;
  late FakeFileRepository repository;
  late UploadNotifier notifier;

  setUp(() {
    picker = FakeFilePickerService();
    repository = FakeFileRepository();
    notifier = UploadNotifier(picker: picker, repository: repository);
  });

  tearDown(() {
    notifier.dispose();
  });

  group('pickFile', () {
    test('sets ready when a valid file is picked', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');

      await notifier.pickFile();

      expect(notifier.state.status, UploadStatus.ready);
      expect(notifier.state.selectedFile?.name, 'test.mp3');
    });

    test('returns to initial when user cancels picker', () async {
      picker.nextFile = null;

      await notifier.pickFile();

      expect(notifier.state.status, UploadStatus.initial);
    });

    test('fails with FileSizeLimitException for oversized file', () async {
      picker.nextFile = fakeFile(size: 501 * 1024 * 1024, extension: 'mp3');

      await notifier.pickFile();

      expect(notifier.state.status, UploadStatus.failure);
      expect(notifier.state.error, isA<FileSizeLimitException>());
    });

    test('fails with UnsupportedFileTypeException for bad extension', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'exe');

      await notifier.pickFile();

      expect(notifier.state.status, UploadStatus.failure);
      expect(notifier.state.error, isA<UnsupportedFileTypeException>());
    });
  });

  group('upload', () {
    test('sets success and response when repository succeeds', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      await notifier.pickFile();

      repository.nextResult = const Result.success(
        UploadResponseModel(
          resourceId: 'res-1',
          taskId: 'task-1',
          name: 'test.mp3',
          type: 'audio',
          status: 'pending',
          sizeBytes: 1024,
          mimeType: 'audio/mpeg',
          createdAt: 1700000000,
        ),
      );

      await notifier.upload();

      expect(notifier.state.status, UploadStatus.success);
      expect(notifier.state.response?.taskId, 'task-1');
      expect(notifier.state.progress, 100);
    });

    test('updates progress via repository callback', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      await notifier.pickFile();

      repository.nextResult = const Result.success(
        UploadResponseModel(
          resourceId: 'res-1',
          taskId: 'task-1',
          name: 'test.mp3',
          type: 'audio',
          status: 'pending',
          sizeBytes: 1024,
          mimeType: 'audio/mpeg',
          createdAt: 1700000000,
        ),
      );

      await notifier.upload();

      expect(notifier.state.progress, greaterThanOrEqualTo(50));
    });

    test('sets failure with NetworkException', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      await notifier.pickFile();

      repository.nextResult = const Result.failure(NetworkException());

      await notifier.upload();

      expect(notifier.state.status, UploadStatus.failure);
      expect(notifier.state.error, isA<NetworkException>());
    });

    test('sets cancelled when CancelledUploadException is returned', () async {
      picker.nextFile = fakeFile(size: 1024, extension: 'mp3');
      await notifier.pickFile();

      repository.nextResult = const Result.failure(CancelledUploadException());

      await notifier.upload();

      expect(notifier.state.status, UploadStatus.cancelled);
    });
  });
}
