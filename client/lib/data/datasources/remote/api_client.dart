import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../../../config/env.dart';
import '../../../domain/repositories/token_provider.dart';
import '../../../shared/errors/app_exception.dart';
import '../../../shared/result.dart';

/// Dio-based HTTP client with envelope unpacking, auth injection and token refresh.
class ApiClient {
  ApiClient({
    required String baseUrl,
    required TokenProvider tokenProvider,
    Dio? dio,
    void Function(String message)? logger,
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
    if (Env.isDev) {
      _dio.interceptors.add(RedactingLogInterceptor(logger: logger));
    }
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

  Future<Result<void>> delete(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return _request<void>(
      () => _dio.delete<dynamic>(path, queryParameters: queryParameters),
      parser: (_) {},
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

  Future<Result<T>> upload<T>(
    String path, {
    required FormData data,
    CancelToken? cancelToken,
    void Function(int sent, int total)? onSendProgress,
    required T Function(dynamic data) parser,
  }) async {
    return _request<T>(
      () => _dio.post<dynamic>(
        path,
        data: data,
        cancelToken: cancelToken,
        onSendProgress: onSendProgress,
      ),
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
    return Result<T>.failure(
      ServerException(
        code: code,
        message: error?['message'] as String?,
        traceId: error?['trace_id'] as String?,
        retryable: error?['retryable'] as bool? ?? false,
      ),
    );
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
        final body = e.response?.data;
        String? errorCode;
        String? message;
        String? traceId;
        bool retryable = false;
        if (body is Map<String, dynamic>) {
          final error = body['error'] as Map<String, dynamic>?;
          errorCode = error?['code'] as String?;
          message = error?['message'] as String?;
          traceId = error?['trace_id'] as String?;
          retryable = error?['retryable'] as bool? ?? false;
        }
        if (status == 401) return const UnauthorizedException();
        if (errorCode == 'TASK_NOT_COMPLETED') {
          return const TaskNotCompletedException();
        }
        return ServerException(
          code: errorCode ?? status?.toString(),
          message: message,
          traceId: traceId,
          retryable: retryable,
        );
      case DioExceptionType.cancel:
        return const CancelledUploadException();
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return const UnknownException();
      case DioExceptionType.badCertificate:
        return const NetworkException();
    }
  }
}

/// Logs HTTP requests and responses without exposing headers or bodies.
class RedactingLogInterceptor extends Interceptor {
  RedactingLogInterceptor({void Function(String message)? logger})
      : _logger = logger ?? _defaultLogger;

  final void Function(String) _logger;

  static void _defaultLogger(String message) => debugPrint(message);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _logger('--> ${options.method} ${options.baseUrl}${options.path}');
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    final request = response.requestOptions;
    _logger(
      '<-- ${response.statusCode} ${request.method} ${request.baseUrl}${request.path}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final request = err.requestOptions;
    _logger(
      '<-- ERROR ${err.response?.statusCode} ${request.method} ${request.baseUrl}${request.path}',
    );
    handler.next(err);
  }
}
