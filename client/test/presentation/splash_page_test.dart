import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/config/constants.dart';
import 'package:mkc_client/presentation/pages/splash_page.dart';

void main() {
  group('SplashPage', () {
    testWidgets('renders loading indicator and app name', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: SplashPage(),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text(Constants.appName), findsOneWidget);
      expect(find.text(Constants.appSubtitle), findsOneWidget);
    });
  });
}
