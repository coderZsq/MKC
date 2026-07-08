import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/auth_api.dart';
import 'package:mkc_client/data/models/auth_token_model.dart';
import 'package:mkc_client/data/models/login_request_model.dart';
import 'package:mkc_client/data/models/register_request_model.dart';
import 'package:mkc_client/data/repositories/auth_repository.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

class _FakeTokenProvider implements TokenProvider {
  String? accessToken;
  String? refreshToken;
  bool cleared = false;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> clearTokens() async {
    cleared = true;
    accessToken = null;
    refreshToken = null;
  }

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }
}

class _FakeAuthApi extends AuthApi {
  Result<AuthTokenModel>? loginResult;
  Result<AuthTokenModel>? registerResult;
  LoginRequestModel? lastLoginRequest;
  RegisterRequestModel? lastRegisterRequest;

  _FakeAuthApi() : super(client: _StubApiClient());

  @override
  Future<Result<AuthTokenModel>> login(LoginRequestModel req) async {
    lastLoginRequest = req;
    return loginResult ??
        const Result.failure(ServerException(code: 'UNEXPECTED'));
  }

  @override
  Future<Result<AuthTokenModel>> register(RegisterRequestModel req) async {
    lastRegisterRequest = req;
    return registerResult ??
        const Result.failure(ServerException(code: 'UNEXPECTED'));
  }
}

class _StubApiClient extends ApiClient {
  _StubApiClient()
      : super(baseUrl: 'http://localhost', tokenProvider: _StubTokenProvider());
}

class _StubTokenProvider implements TokenProvider {
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

void main() {
  group('AuthRepository', () {
    late _FakeAuthApi authApi;
    late _FakeTokenProvider tokenProvider;
    late AuthRepository repository;

    setUp(() {
      authApi = _FakeAuthApi();
      tokenProvider = _FakeTokenProvider();
      repository = AuthRepository(
        authApi: authApi,
        tokenProvider: tokenProvider,
      );
    });

    const token = AuthTokenModel(
      accessToken: 'access-123',
      refreshToken: 'refresh-123',
      expiresIn: 3600,
      tokenType: 'Bearer',
    );

    test('login persists tokens on success', () async {
      authApi.loginResult = const Result.success(token);

      final result = await repository.login(
        email: 'user@example.com',
        password: 'Password1',
      );

      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
      expect(authApi.lastLoginRequest?.email, equals('user@example.com'));
      expect(authApi.lastLoginRequest?.password, equals('Password1'));
      expect(tokenProvider.accessToken, equals('access-123'));
      expect(tokenProvider.refreshToken, equals('refresh-123'));
    });

    test('login returns failure when API fails', () async {
      authApi.loginResult = const Result.failure(
        UnauthorizedException(),
      );

      final result = await repository.login(
        email: 'user@example.com',
        password: 'wrong',
      );

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(tokenProvider.accessToken, isNull);
    });

    test('register persists tokens on success', () async {
      authApi.registerResult = const Result.success(token);

      final result = await repository.register(
        email: 'user@example.com',
        password: 'Password1',
        nickname: 'User',
      );

      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
      expect(authApi.lastRegisterRequest?.email, equals('user@example.com'));
      expect(authApi.lastRegisterRequest?.nickname, equals('User'));
      expect(tokenProvider.accessToken, equals('access-123'));
    });

    test('register returns CONFLICT failure without persisting tokens',
        () async {
      authApi.registerResult = const Result.failure(
        ServerException(code: 'CONFLICT'),
      );

      final result = await repository.register(
        email: 'exists@example.com',
        password: 'Password1',
      );

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(tokenProvider.accessToken, isNull);
    });

    test('isAuthenticated returns true when access token exists', () async {
      tokenProvider.accessToken = 'token';
      expect(await repository.isAuthenticated(), isTrue);
    });

    test('isAuthenticated returns false when access token is missing',
        () async {
      expect(await repository.isAuthenticated(), isFalse);
    });

    test('logout clears stored tokens', () async {
      tokenProvider.accessToken = 'token';
      await repository.logout();
      expect(tokenProvider.cleared, isTrue);
      expect(tokenProvider.accessToken, isNull);
    });
  });
}
