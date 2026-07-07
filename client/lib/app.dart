import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'config/constants.dart';
import 'config/theme.dart';
import 'presentation/pages/home_page.dart';
import 'presentation/pages/splash_page.dart';
import 'presentation/routes/app_routes.dart';

/// Root application widget configured with Riverpod, go_router and app themes.
class MKCApp extends StatelessWidget {
  const MKCApp({super.key});

  @override
  Widget build(BuildContext context) {
    final router = GoRouter(
      initialLocation: splashRoute,
      routes: [
        GoRoute(
          path: splashRoute,
          builder: (context, state) => const SplashPage(),
        ),
        GoRoute(
          path: homeRoute,
          builder: (context, state) => const HomePage(),
        ),
      ],
    );

    return ProviderScope(
      child: MaterialApp.router(
        title: Constants.appName,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        routerConfig: router,
      ),
    );
  }
}
