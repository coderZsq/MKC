import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/config/constants.dart';
import 'package:mkc_client/presentation/pages/splash_page.dart';
import 'package:mkc_client/presentation/providers/auth_provider.dart';

import '../shared/auth_test_helpers.dart';

void main() {
  group('SplashPage', () {
    testWidgets('renders loading indicator and app name', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authNotifierProvider.overrideWith((ref) => FakeAuthNotifier()),
          ],
          child: const MaterialApp(
            home: SplashPage(),
          ),
        ),
      );
      await tester.pump(const Duration(seconds: 1));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text(Constants.appName), findsOneWidget);
      expect(find.text(Constants.appSubtitle), findsOneWidget);
    });
  });
}
