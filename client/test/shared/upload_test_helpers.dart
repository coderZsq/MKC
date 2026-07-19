import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:mkc_client/data/models/upload_response_model.dart';
import 'package:mkc_client/data/repositories/file_repository.dart';
import 'package:mkc_client/domain/entities/picked_file.dart';
import 'package:mkc_client/domain/services/file_picker_service.dart';
import 'package:mkc_client/shared/result.dart';

class FakeFilePickerService implements FilePickerService {
  PickedFile? nextFile;
  Object? nextError;
  int pickCount = 0;

  @override
  Future<PickedFile?> pickSingleFile() async {
    pickCount++;
    final error = nextError;
    if (error != null) {
      throw error;
    }
    return nextFile;
  }
}

class FakeFileRepository implements FileRepository {
  Result<UploadResponseModel>? nextResult;
  PickedFile? lastFile;
  bool? lastAutoSummary;
  CancelToken? lastCancelToken;
  void Function(int sent, int total)? lastOnProgress;

  @override
  Future<Result<UploadResponseModel>> uploadFile({
    required PickedFile file,
    required bool autoSummary,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) async {
    lastFile = file;
    lastAutoSummary = autoSummary;
    lastCancelToken = cancelToken;
    lastOnProgress = onProgress;

    onProgress(50, 100);

    final result = nextResult ??
        const Result.success(
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

    result.when(
      success: (_) {},
      failure: (_) {},
    );

    return result;
  }
}

PickedFile fakeFile({
  String? path,
  String name = 'test.mp3',
  int size = 1024,
  String extension = 'mp3',
}) =>
    PickedFile(
      path: path,
      bytes: path == null ? Uint8List(0) : null,
      name: name,
      size: size,
      extension: extension,
    );
