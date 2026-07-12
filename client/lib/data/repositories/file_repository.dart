import 'package:dio/dio.dart';

import '../datasources/remote/file_api.dart';
import '../models/upload_response_model.dart';
import '../../domain/entities/picked_file.dart';
import '../../shared/result.dart';

/// Coordinates file upload API calls.
class FileRepository {
  FileRepository({required FileApi api}) : _api = api;

  final FileApi _api;

  Future<Result<UploadResponseModel>> uploadFile({
    required PickedFile file,
    required bool autoSummary,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) {
    return _api.upload(
      file: file,
      autoSummary: autoSummary,
      cancelToken: cancelToken,
      onProgress: onProgress,
    );
  }
}
