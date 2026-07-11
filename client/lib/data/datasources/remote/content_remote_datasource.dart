import 'package:dio/dio.dart';

import '../../../config/env.dart';
import '../../../shared/errors/app_exception.dart';
import '../../../shared/result.dart';

/// Downloads result file content from signed URLs.
class ContentRemoteDataSource {
  ContentRemoteDataSource({
    Dio? dio,
    String? expectedHost,
  })  : _dio = dio ?? Dio(),
        _expectedHost = expectedHost ?? Env.storageHost {
    _dio.options.followRedirects = false;
    _dio.options.validateStatus = (status) => status != null && status < 400;
  }

  final Dio _dio;
  final String _expectedHost;
  final Map<String, String> _cache = {};

  /// Downloads the text content at [url] as a plain string.
  Future<Result<String>> downloadText(String url) async {
    if (!_isAllowedUrl(url)) {
      return const Result<String>.failure(UnsafeUrlException());
    }

    final cached = _cache[url];
    if (cached != null) {
      return Result<String>.success(cached);
    }

    try {
      final response = await _dio.get<String>(
        url,
        options: Options(responseType: ResponseType.plain),
      );
      final text = response.data ?? '';
      _cache[url] = text;
      return Result<String>.success(text);
    } on DioException catch (e) {
      return Result<String>.failure(_mapDioException(e));
    } on Exception {
      return const Result<String>.failure(UnknownException());
    }
  }

  bool _isAllowedUrl(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return false;
    if (uri.scheme != 'http' && uri.scheme != 'https') return false;
    if (Env.isProd && uri.scheme != 'https') return false;
    if (_expectedHost.isNotEmpty && uri.host != _expectedHost) return false;
    return true;
  }

  AppException _mapDioException(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return const NetworkException();
      case DioExceptionType.badResponse:
        final status = e.response?.statusCode;
        if (status == 401) return const UnauthorizedException();
        return ServerException(code: status?.toString());
      case DioExceptionType.cancel:
        return const UnknownException();
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return const UnknownException();
      case DioExceptionType.badCertificate:
        return const NetworkException();
    }
  }
}
