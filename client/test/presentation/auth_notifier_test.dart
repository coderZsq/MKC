import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/repositories/auth_repository.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/auth_api.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/presentation/providers/auth_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

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

class _StubApiClient extends ApiClient {
  _StubApiClient()
      : super(baseUrl: 'http://localhost', tokenProvider: _StubTokenProvider());
}

class _StubAuthApi extends AuthApi {
  _StubAuthApi() : super(client: _StubApiClient());
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(authApi: _StubAuthApi(), tokenProvider: _StubTokenProvider());

  Result<void>? loginResult;
  Result<void>? registerResult;

  String? lastEmail;
  String? lastPassword;
  String? lastNickname;
  bool isAuthenticatedValue = false;

  @override
  Future<Result<void>> login({
    required String email,
    required String password,
  }) async {
    lastEmail = email;
    lastPassword = password;
    return loginResult ?? const Result.success(null);
  }

  @override
  Future<Result<void>> register({
    required String email,
    required String password,
    String? nickname,
  }) async {
    lastEmail = email;
    lastPassword = password;
    lastNickname = nickname;
    return registerResult ?? const Result.success(null);
  }

  @override
  Future<bool> isAuthenticated() async => isAuthenticatedValue;

  @override
  Future<void> logout() async {}
}

void main() {
  group('AuthNotifier', () {
    late _FakeAuthRepository repository;
    late AuthNotifier notifier;

    setUp(() {
      repository = _FakeAuthRepository();
      notifier = AuthNotifier(repo: repository);
    });

    test('initial state is not loading and not authenticated', () {
      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isFalse);
      expect(notifier.state.status, AuthScreenStatus.unknown);
      expect(notifier.state.error, isNull);
    });

    test('checkAuthentication sets authenticated when token exists', () async {
      repository.isAuthenticatedValue = true;
      final future = notifier.checkAuthentication();

      expect(notifier.state.isLoading, isTrue);

      await future;

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isTrue);
      expect(notifier.state.status, AuthScreenStatus.authenticated);
      expect(notifier.state.error, isNull);
    });

    test('checkAuthentication sets unauthenticated when no token', () async {
      repository.isAuthenticatedValue = false;
      await notifier.checkAuthentication();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isFalse);
      expect(notifier.state.status, AuthScreenStatus.unauthenticated);
      expect(notifier.state.error, isNull);
    });

    test('login success updates state to authenticated', () async {
      await notifier.login('user@example.com', 'Password1');

      expect(repository.lastEmail, equals('user@example.com'));
      expect(repository.lastPassword, equals('Password1'));
      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isTrue);
      expect(notifier.state.status, AuthScreenStatus.authenticated);
      expect(notifier.state.error, isNull);
    });

    test('login failure keeps error and unauthenticated', () async {
      repository.loginResult = const Result.failure(
        UnauthorizedException(),
      );
      await notifier.login('user@example.com', 'wrongpass');

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isFalse);
      expect(notifier.state.status, AuthScreenStatus.unauthenticated);
      expect(notifier.state.error, isA<UnauthorizedException>());
    });

    test('register success updates state to authenticated', () async {
      await notifier.register('user@example.com', 'Password1',
          nickname: 'User');

      expect(repository.lastEmail, equals('user@example.com'));
      expect(repository.lastPassword, equals('Password1'));
      expect(repository.lastNickname, equals('User'));
      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isTrue);
      expect(notifier.state.status, AuthScreenStatus.authenticated);
      expect(notifier.state.error, isNull);
    });

    test('register failure keeps error and unauthenticated', () async {
      repository.registerResult = const Result.failure(
        ServerException(code: 'CONFLICT'),
      );
      await notifier.register('user@example.com', 'Password1');

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.isAuthenticated, isFalse);
      expect(notifier.state.status, AuthScreenStatus.unauthenticated);
      expect(notifier.state.error, isA<ServerException>());
    });

    test('clearError removes error from state', () async {
      repository.loginResult = const Result.failure(
        NetworkException(),
      );
      await notifier.login('user@example.com', 'Password1');
      expect(notifier.state.error, isNotNull);

      notifier.clearError();

      expect(notifier.state.error, isNull);
      expect(notifier.state.isLoading, isFalse);
    });
  });
}
