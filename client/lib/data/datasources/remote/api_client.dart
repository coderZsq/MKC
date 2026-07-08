import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../../../domain/repositories/token_provider.dart';
import '../../../shared/errors/app_exception.dart';
import '../../../shared/result.dart';

/// Dio-based HTTP client with envelope unpacking, auth injection and token refresh.
class ApiClient {
  ApiClient({
    required String baseUrl,
    required TokenProvider tokenProvider,
    Dio? dio,
  })  : _tokenProvider = tokenProvider,
        _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: baseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 30),
                headers: <String, String>{
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                },
              ),
            ) {
    _dio.interceptors.add(_authInterceptor());
    _dio.interceptors
        .add(LogInterceptor(requestBody: true, responseBody: true));
  }

  final Dio _dio;
  final TokenProvider _tokenProvider;
  final _uuid = const Uuid();

  Interceptor _authInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _tokenProvider.getAccessToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        options.headers['X-Request-ID'] = _uuid.v4();
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _tokenProvider.refreshAccessToken();
          if (refreshed) {
            final token = await _tokenProvider.getAccessToken();
            final requestOptions = error.requestOptions;
            requestOptions.headers['Authorization'] = 'Bearer $token';
            return handler.resolve(await _dio.fetch(requestOptions));
          }
        }
        handler.next(error);
      },
    );
  }

  Future<Result<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    required T Function(dynamic data) parser,
  }) async {
    return _request<T>(
      () => _dio.get<dynamic>(path, queryParameters: queryParameters),
      parser: parser,
    );
  }

  Future<Result<T>> post<T>(
    String path, {
    dynamic data,
    required T Function(dynamic data) parser,
  }) async {
    return _request<T>(
      () => _dio.post<dynamic>(path, data: data),
      parser: parser,
    );
  }

  Future<Result<T>> _request<T>(
    Future<Response<dynamic>> Function() call, {
    required T Function(dynamic data) parser,
  }) async {
    try {
      final response = await call();
      return _unpackEnvelope(response, parser);
    } on DioException catch (e) {
      return Result<T>.failure(_mapDioException(e));
    } on Exception {
      return Result<T>.failure(const UnknownException());
    }
  }

  Result<T> _unpackEnvelope<T>(
    Response<dynamic> response,
    T Function(dynamic data) parser,
  ) {
    final body = response.data;
    if (body is! Map<String, dynamic>) {
      return Result<T>.failure(const ServerException());
    }

    final success = body['success'] as bool? ?? false;
    if (success) {
      return Result<T>.success(parser(body['data']));
    }

    final error = body['error'] as Map<String, dynamic>?;
    final code = error?['code'] as String?;
    return Result<T>.failure(ServerException(code: code));
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
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return const UnknownException();
      case DioExceptionType.badCertificate:
        return const NetworkException();
    }
  }
}
