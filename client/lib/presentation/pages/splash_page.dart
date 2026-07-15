import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:go_router/go_router.dart';

import '../../config/constants.dart';
import '../../config/theme.dart';
import '../providers/auth_provider.dart';
import '../routes/app_routes.dart';

/// Launch screen shown while the app initializes.
class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await ref.read(authNotifierProvider.notifier).checkAuthentication();
      if (!mounted) return;
      final status = ref.read(authNotifierProvider).status;
      GoRouter.maybeOf(context)?.go(
        status == AuthScreenStatus.authenticated ? homeRoute : loginRoute,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: ClaudeColors.terracotta,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text(
                  'M',
                  style: TextStyle(
                    color: ClaudeColors.ivory,
                    fontFamily: ClaudeFonts.serif,
                    fontSize: 28,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              Constants.appName,
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 8),
            Text(
              Constants.appSubtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: ClaudeColors.oliveGray,
                  ),
            ),
            const SizedBox(height: 28),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
