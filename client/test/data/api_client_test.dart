import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';

class _FakeTokenProvider implements TokenProvider {
  String? _token;
  int refreshCalls = 0;

  void setToken(String? value) => _token = value;

  @override
  Future<String?> getAccessToken() async => _token;

  @override
  Future<bool> refreshAccessToken() async {
    refreshCalls++;
    _token = 'refreshed-token';
    return true;
  }

  @override
  Future<void> clearTokens() async {
    _token = null;
  }

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    _token = accessToken;
  }
}

class _FailingRefreshProvider implements TokenProvider {
  _FailingRefreshProvider(this._token);

  final String? _token;

  @override
  Future<String?> getAccessToken() async => _token;

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

class _MockAdapter implements HttpClientAdapter {
  _MockAdapter({required this.onFetch});

  final ResponseBody Function(RequestOptions options) onFetch;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return onFetch(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _jsonBody(Object body, {required int statusCode}) {
  final bytes = Uint8List.fromList(utf8.encode(jsonEncode(body)));
  return ResponseBody.fromBytes(
    bytes,
    statusCode,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

void main() {
  group('ApiClient', () {
    late _FakeTokenProvider tokenProvider;
    late Dio dio;

    setUp(() {
      tokenProvider = _FakeTokenProvider()..setToken('initial-token');
      dio = Dio(BaseOptions(baseUrl: 'http://localhost:8080'));
    });

    test('injects bearer token and returns parsed data on 200', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.headers['Authorization'], 'Bearer initial-token');
          return _jsonBody(
            {'success': true, 'data': 42, 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final client = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: tokenProvider,
        dio: dio,
      );

      final result = await client.get<int>(
        '/test',
        parser: (dynamic data) => data as int,
      );

      expect(
        result.when(success: (data) => data, failure: (_) => -1),
        equals(42),
      );
    });

    test('refreshes token on 401 and retries the request', () async {
      var requestCount = 0;
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          requestCount++;
          if (requestCount == 1) {
            return _jsonBody(
              {
                'success': false,
                'data': null,
                'error': {'code': 'UNAUTHORIZED', 'message': 'expired'},
                'meta': null,
              },
              statusCode: 401,
            );
          }
          expect(options.headers['Authorization'], 'Bearer refreshed-token');
          return _jsonBody(
            {'success': true, 'data': 'ok', 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final client = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: tokenProvider,
        dio: dio,
      );

      final result = await client.get<String>(
        '/test',
        parser: (dynamic data) => data as String,
      );

      expect(tokenProvider.refreshCalls, equals(1));
      expect(
        result.when(success: (data) => data, failure: (_) => 'failed'),
        equals('ok'),
      );
      expect(requestCount, equals(2));
    });

    test('returns failure when refresh fails after 401', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (_) => _jsonBody(
          {
            'success': false,
            'data': null,
            'error': {'code': 'UNAUTHORIZED', 'message': 'expired'},
            'meta': null,
          },
          statusCode: 401,
        ),
      );

      final client = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: _FailingRefreshProvider('initial-token'),
        dio: dio,
      );

      final result = await client.get<int>(
        '/test',
        parser: (dynamic data) => data as int,
      );

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
    });

    test('maps unified error payload fields', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (_) => _jsonBody(
          {
            'success': false,
            'data': null,
            'error': {
              'code': 'LLM_TIMEOUT',
              'message': '模型响应超时，请稍后重试',
              'trace_id': 'trace-1',
              'retryable': true,
            },
            'meta': null,
          },
          statusCode: 504,
        ),
      );

      final client = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: tokenProvider,
        dio: dio,
      );

      final result = await client.get<int>(
        '/test',
        parser: (dynamic data) => data as int,
      );

      final error = result.when<AppException?>(
        success: (_) => null,
        failure: (error) => error,
      );
      expect(error, isA<ServerException>());
      final serverError = error! as ServerException;
      expect(serverError.code, 'LLM_TIMEOUT');
      expect(serverError.traceId, 'trace-1');
      expect(serverError.retryable, isTrue);
      expect(serverError.message, '模型响应超时，请稍后重试');
    });

    test('logs requests and responses without exposing tokens or bodies',
        () async {
      final logs = <String>[];
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          return _jsonBody(
            {'success': true, 'data': 42, 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final client = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: tokenProvider,
        dio: dio,
        logger: logs.add,
      );

      await client.get<int>(
        '/test',
        parser: (dynamic data) => data as int,
      );

      expect(logs.length, greaterThanOrEqualTo(2));
      expect(logs.first, contains('--> GET'));
      expect(logs[1], contains('<-- 200'));
      for (final log in logs) {
        expect(log, isNot(contains('initial-token')));
        expect(log, isNot(contains('42')));
      }
    });
  });
}
