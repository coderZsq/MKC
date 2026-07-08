import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/auth_api.dart';
import 'package:mkc_client/data/repositories/auth_repository.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/presentation/providers/auth_provider.dart';
import 'package:mkc_client/presentation/routes/app_router.dart';
import 'package:mkc_client/shared/result.dart';

class FakeAuthNotifier extends AuthNotifier {
  FakeAuthNotifier() : super(repo: _FakeAuthRepository());

  Result<void>? nextLoginResult;
  Result<void>? nextRegisterResult;
  bool nextAuthStatus = false;

  String? lastEmail;
  String? lastPassword;
  String? lastNickname;

  @override
  Future<void> checkAuthentication() async {
    state = state.copyWith(isLoading: true, error: null);
    await Future<void>.delayed(Duration.zero);
    state = state.copyWith(
      isLoading: false,
      isAuthenticated: nextAuthStatus,
      status: nextAuthStatus
          ? AuthScreenStatus.authenticated
          : AuthScreenStatus.unauthenticated,
      error: null,
    );
  }

  @override
  Future<void> login(String email, String password) async {
    lastEmail = email;
    lastPassword = password;
    state = state.copyWith(isLoading: true, error: null);
    await Future<void>.delayed(Duration.zero);
    final result = nextLoginResult ?? const Result.success(null);
    state = result.when(
      success: (_) => state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        status: AuthScreenStatus.authenticated,
        error: null,
      ),
      failure: (err) => state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        status: AuthScreenStatus.unauthenticated,
        error: err,
      ),
    );
  }

  @override
  Future<void> register(
    String email,
    String password, {
    String? nickname,
  }) async {
    lastEmail = email;
    lastPassword = password;
    lastNickname = nickname;
    state = state.copyWith(isLoading: true, error: null);
    await Future<void>.delayed(Duration.zero);
    final result = nextRegisterResult ?? const Result.success(null);
    state = result.when(
      success: (_) => state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        status: AuthScreenStatus.authenticated,
        error: null,
      ),
      failure: (err) => state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        status: AuthScreenStatus.unauthenticated,
        error: err,
      ),
    );
  }
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(
          authApi: _StubAuthApi(),
          tokenProvider: _StubTokenProvider(),
        );
}

class _StubAuthApi extends AuthApi {
  _StubAuthApi() : super(client: _StubApiClient());
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

Future<void> pumpWithAuthNotifier(
  WidgetTester tester,
  FakeAuthNotifier notifier,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authNotifierProvider.overrideWith((ref) => notifier),
      ],
      child: const _TestRouterApp(),
    ),
  );
  await tester.pumpAndSettle();
}

class _TestRouterApp extends ConsumerWidget {
  const _TestRouterApp();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      routerConfig: ref.watch(routerProvider),
    );
  }
}

const String loginRoute = '/login';
const String registerRoute = '/register';
const String homeRoute = '/';
const String splashRoute = '/splash';
