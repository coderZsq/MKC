import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/datasources/remote/auth_api.dart';
import '../../data/repositories/auth_repository.dart';
import '../../shared/errors/app_exception.dart';
import '../../shared/result.dart';
import '../providers/app_provider.dart';

/// Overall authentication screen status used by the router.
enum AuthScreenStatus { unknown, authenticated, unauthenticated }

/// Auth state for the application.
class AuthState {
  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.status = AuthScreenStatus.unknown,
    this.error,
  });

  final bool isLoading;
  final bool isAuthenticated;
  final AuthScreenStatus status;
  final AppException? error;

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    AuthScreenStatus? status,
    AppException? error,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      status: status ?? this.status,
      error: error,
    );
  }
}

/// Manages authentication state transitions.
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier({required AuthRepository repo})
      : _repo = repo,
        super(const AuthState());

  final AuthRepository _repo;

  Future<void> checkAuthentication() async {
    state = state.copyWith(isLoading: true, error: null);
    final isAuth = await _repo.isAuthenticated();
    state = state.copyWith(
      isLoading: false,
      isAuthenticated: isAuth,
      status: isAuth
          ? AuthScreenStatus.authenticated
          : AuthScreenStatus.unauthenticated,
      error: null,
    );
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repo.login(email: email, password: password);
    state = _handleAuthResult(result);
  }

  Future<void> register(
    String email,
    String password, {
    String? nickname,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repo.register(
      email: email,
      password: password,
      nickname: nickname,
    );
    state = _handleAuthResult(result);
  }

  AuthState _handleAuthResult(Result<void> result) {
    return result.when(
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

  void clearError() => state = state.copyWith(error: null);
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final api = AuthApi(client: ref.watch(apiClientProvider));
  final storage = ref.watch(tokenProvider);
  return AuthRepository(authApi: api, tokenProvider: storage);
});

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(repo: ref.watch(authRepositoryProvider)),
);
