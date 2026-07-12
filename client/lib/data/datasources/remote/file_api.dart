import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import '../../../domain/entities/picked_file.dart';
import '../../../shared/result.dart';
import '../../../shared/validators/file_validator.dart';
import 'api_client.dart';
import '../../models/upload_response_model.dart';

/// Remote file API endpoints.
class FileApi {
  FileApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  Future<Result<UploadResponseModel>> upload({
    required PickedFile file,
    required bool autoSummary,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) async {
    final multipartFile = await _toMultipartFile(file);
    final formData = FormData.fromMap({
      'file': multipartFile,
      'auto_summary': autoSummary.toString(),
    });

    return _client.upload<UploadResponseModel>(
      '/files/upload',
      data: formData,
      cancelToken: cancelToken,
      onSendProgress: onProgress,
      parser: (dynamic data) =>
          UploadResponseModel.fromJson(data as Map<String, dynamic>),
    );
  }

  Future<MultipartFile> _toMultipartFile(PickedFile file) async {
    if (file.bytes case final bytes?) {
      return MultipartFile.fromBytes(
        bytes,
        filename: file.name,
        contentType: _mediaTypeFromExtension(file.extension),
      );
    }
    if (file.path case final path?) {
      return MultipartFile.fromFile(
        path,
        filename: file.name,
        contentType: _mediaTypeFromExtension(file.extension),
      );
    }
    throw ArgumentError('PickedFile must provide either path or bytes');
  }

  MediaType? _mediaTypeFromExtension(String? extension) {
    final mime = mimeFromExtension(extension);
    return mime == null ? null : MediaType.parse(mime);
  }
}
