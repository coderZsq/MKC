import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../pages/home_page.dart';
import '../pages/login_page.dart';
import '../pages/register_page.dart';
import '../pages/splash_page.dart';
import '../providers/auth_provider.dart';
import 'app_routes.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<AuthScreenStatus>(
    ref.read(authNotifierProvider).status,
  );

  ref.listen<AuthState>(
    authNotifierProvider,
    (_, next) => refresh.value = next.status,
  );

  return GoRouter(
    initialLocation: splashRoute,
    refreshListenable: refresh,
    redirect: (context, state) {
      final status = ref.read(authNotifierProvider).status;
      final path = state.uri.path;

      if (status == AuthScreenStatus.unknown) {
        return splashRoute;
      }
      if (status == AuthScreenStatus.authenticated) {
        if (path == loginRoute || path == registerRoute) return homeRoute;
        return null;
      }
      // unauthenticated
      if (path == loginRoute || path == registerRoute) return null;
      return loginRoute;
    },
    routes: [
      GoRoute(path: splashRoute, builder: (_, __) => const SplashPage()),
      GoRoute(path: loginRoute, builder: (_, __) => const LoginPage()),
      GoRoute(path: registerRoute, builder: (_, __) => const RegisterPage()),
      GoRoute(path: homeRoute, builder: (_, __) => const HomePage()),
    ],
  );
});
