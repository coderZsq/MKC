import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/auth_api.dart';
import 'package:mkc_client/data/models/login_request_model.dart';
import 'package:mkc_client/data/models/register_request_model.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';

class _FakeTokenProvider implements TokenProvider {
  @override
  Future<String?> getAccessToken() async => null;

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

const _tokenJson = {
  'access_token': 'access-123',
  'refresh_token': 'refresh-123',
  'expires_in': 3600,
  'token_type': 'Bearer',
};

void main() {
  group('AuthApi', () {
    late Dio dio;
    late AuthApi authApi;

    setUp(() {
      dio = Dio(BaseOptions(baseUrl: 'http://localhost:8080'));
      final apiClient = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: _FakeTokenProvider(),
        dio: dio,
      );
      authApi = AuthApi(client: apiClient);
    });

    test('login sends correct payload and parses token response', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/auth/login'));
          expect(options.method, equals('POST'));
          expect(
            options.data,
            equals({'email': 'user@example.com', 'password': 'Password1'}),
          );
          return _jsonBody(
            {'success': true, 'data': _tokenJson, 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final result = await authApi.login(
        const LoginRequestModel(
          email: 'user@example.com',
          password: 'Password1',
        ),
      );

      result.when(
        success: (token) {
          expect(token.accessToken, equals('access-123'));
          expect(token.refreshToken, equals('refresh-123'));
          expect(token.expiresIn, equals(3600));
          expect(token.tokenType, equals('Bearer'));
        },
        failure: (_) => fail('expected success'),
      );
    });

    test('register sends correct payload and parses token response', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/auth/register'));
          expect(options.method, equals('POST'));
          expect(
            options.data,
            equals({
              'email': 'user@example.com',
              'password': 'Password1',
              'nickname': 'User',
            }),
          );
          return _jsonBody(
            {'success': true, 'data': _tokenJson, 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final result = await authApi.register(
        const RegisterRequestModel(
          email: 'user@example.com',
          password: 'Password1',
          nickname: 'User',
        ),
      );

      result.when(
        success: (token) {
          expect(token.accessToken, equals('access-123'));
        },
        failure: (_) => fail('expected success'),
      );
    });

    test('register omits null nickname', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.data, isNot(contains('nickname')));
          return _jsonBody(
            {'success': true, 'data': _tokenJson, 'error': null, 'meta': null},
            statusCode: 200,
          );
        },
      );

      final result = await authApi.register(
        const RegisterRequestModel(
          email: 'user@example.com',
          password: 'Password1',
        ),
      );

      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
    });
  });
}
