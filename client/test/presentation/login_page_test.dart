import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/pages/home_page.dart';
import 'package:mkc_client/presentation/pages/login_page.dart';
import 'package:mkc_client/presentation/pages/register_page.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../shared/auth_test_helpers.dart';

void main() {
  group('LoginPage', () {
    late FakeAuthNotifier notifier;

    setUp(() {
      notifier = FakeAuthNotifier();
    });

    Future<void> pumpLoginPage(WidgetTester tester) async {
      notifier.nextAuthStatus = false;
      await pumpWithAuthNotifier(tester, notifier);
      // After splash check, router should land on login.
      expect(find.byType(LoginPage), findsOneWidget);
    }

    Future<void> enterCredentials(
      WidgetTester tester, {
      String email = '',
      String password = '',
    }) async {
      final emailField = find.byType(TextFormField).first;
      final passwordField = find.byType(TextFormField).last;
      await tester.enterText(emailField, email);
      await tester.enterText(passwordField, password);
      await tester.pump();
    }

    testWidgets('shows required email error', (tester) async {
      await pumpLoginPage(tester);
      await tester.tap(find.text('登录'));
      await tester.pump();
      expect(find.text('请输入邮箱'), findsAtLeastNWidgets(2));
    });

    testWidgets('shows invalid email error', (tester) async {
      await pumpLoginPage(tester);
      await enterCredentials(tester, email: 'not-email');
      await tester.tap(find.text('登录'));
      await tester.pump();
      expect(find.text('邮箱格式不正确'), findsOneWidget);
    });

    testWidgets('shows password length error', (tester) async {
      await pumpLoginPage(tester);
      await enterCredentials(
        tester,
        email: 'user@example.com',
        password: 'short1',
      );
      await tester.tap(find.text('登录'));
      await tester.pump();
      expect(find.text('密码至少 8 位'), findsOneWidget);
    });

    testWidgets('shows password format error', (tester) async {
      await pumpLoginPage(tester);
      await enterCredentials(
        tester,
        email: 'user@example.com',
        password: '12345678',
      );
      await tester.tap(find.text('登录'));
      await tester.pump();
      expect(find.text('密码需同时包含字母和数字'), findsOneWidget);
    });

    testWidgets('successful login navigates to home', (tester) async {
      await pumpLoginPage(tester);
      await enterCredentials(
        tester,
        email: 'user@example.com',
        password: 'Password1',
      );

      await tester.tap(find.text('登录'));
      await tester.pumpAndSettle();

      expect(find.byType(HomePage), findsOneWidget);
      expect(notifier.lastEmail, equals('user@example.com'));
      expect(notifier.lastPassword, equals('Password1'));
    });

    testWidgets('shows unauthorized error on failure', (tester) async {
      notifier.nextLoginResult = const Result.failure(
        UnauthorizedException(),
      );
      await pumpLoginPage(tester);
      await enterCredentials(
        tester,
        email: 'user@example.com',
        password: 'Password1',
      );

      await tester.tap(find.text('登录'));
      await tester.pumpAndSettle();

      expect(find.byType(LoginPage), findsOneWidget);
      expect(find.text('邮箱或密码错误'), findsOneWidget);
    });

    testWidgets('shows network error', (tester) async {
      notifier.nextLoginResult = const Result.failure(
        NetworkException(),
      );
      await pumpLoginPage(tester);
      await enterCredentials(
        tester,
        email: 'user@example.com',
        password: 'Password1',
      );

      await tester.tap(find.text('登录'));
      await tester.pumpAndSettle();

      expect(find.text('网络异常，请检查连接'), findsOneWidget);
    });

    testWidgets('navigates to register page', (tester) async {
      await pumpLoginPage(tester);
      await tester.tap(find.text('还没有账号？去注册'));
      await tester.pumpAndSettle();
      expect(find.byType(RegisterPage), findsOneWidget);
    });
  });
}
