import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/presentation/pages/home_page.dart';
import 'package:mkc_client/presentation/pages/splash_page.dart';
import 'package:mkc_client/presentation/providers/auth_provider.dart';

import 'shared/auth_test_helpers.dart';

void main() {
  testWidgets('SplashPage renders loading indicator and title', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authNotifierProvider.overrideWith((ref) => FakeAuthNotifier()),
        ],
        child: const MaterialApp(home: SplashPage()),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('MKC'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('HomePage renders placeholder text', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: HomePage()));

    expect(find.text('首页占位 — 功能开发中'), findsOneWidget);
  });

  testWidgets('MKCApp builds with router', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authNotifierProvider.overrideWith((ref) => FakeAuthNotifier()),
        ],
        child: const MKCApp(),
      ),
    );

    expect(find.byType(SplashPage), findsOneWidget);
    await tester.pumpAndSettle();
  });
}
