import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/errors/app_exception.dart';

/// Auth state for the application.
class AuthState {
  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.error,
  });

  final bool isLoading;
  final bool isAuthenticated;
  final AppException? error;

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    AppException? error,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      error: error,
    );
  }
}

/// Manages authentication state transitions.
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState());

  Future<void> checkAuthentication() async {
    state = state.copyWith(isLoading: true, error: null);

    // TODO(S1): verify stored token validity.
    await Future<void>.delayed(const Duration(milliseconds: 300));

    state = state.copyWith(isLoading: false, isAuthenticated: false);
  }

  void setAuthenticated(bool value) {
    state = state.copyWith(isAuthenticated: value, error: null);
  }
}

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);
