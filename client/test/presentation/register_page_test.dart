import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/pages/home_page.dart';
import 'package:mkc_client/presentation/pages/login_page.dart';
import 'package:mkc_client/presentation/pages/register_page.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../shared/auth_test_helpers.dart';

void main() {
  group('RegisterPage', () {
    late FakeAuthNotifier notifier;

    setUp(() {
      notifier = FakeAuthNotifier();
    });

    Future<void> pumpRegisterPage(WidgetTester tester) async {
      notifier.nextAuthStatus = false;
      await pumpWithAuthNotifier(tester, notifier);
      await tester.tap(find.text('还没有账号？去注册'));
      await tester.pumpAndSettle();
      expect(find.byType(RegisterPage), findsOneWidget);
    }

    Future<void> enterFields(
      WidgetTester tester, {
      String email = '',
      String nickname = '',
      String password = '',
      String confirmPassword = '',
    }) async {
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), email);
      await tester.enterText(fields.at(1), nickname);
      await tester.enterText(fields.at(2), password);
      await tester.enterText(fields.at(3), confirmPassword);
      await tester.pump();
    }

    testWidgets('shows confirm password mismatch error', (tester) async {
      await pumpRegisterPage(tester);
      await enterFields(
        tester,
        email: 'user@example.com',
        password: 'Passw0rd!',
        confirmPassword: 'Password1!',
      );
      await tester.tap(find.text('注册'));
      await tester.pump();
      expect(find.text('两次输入的密码不一致'), findsOneWidget);
    });

    testWidgets('successful registration navigates to home', (tester) async {
      await pumpRegisterPage(tester);
      await enterFields(
        tester,
        email: 'user@example.com',
        nickname: 'User',
        password: 'Password1',
        confirmPassword: 'Password1',
      );

      await tester.tap(find.text('注册'));
      await tester.pumpAndSettle();

      expect(find.byType(HomePage), findsOneWidget);
      expect(notifier.lastEmail, equals('user@example.com'));
      expect(notifier.lastPassword, equals('Password1'));
      expect(notifier.lastNickname, equals('User'));
    });

    testWidgets('shows conflict error when email already registered', (
      tester,
    ) async {
      notifier.nextRegisterResult = const Result.failure(
        ServerException(code: 'CONFLICT'),
      );
      await pumpRegisterPage(tester);
      await enterFields(
        tester,
        email: 'exists@example.com',
        password: 'Password1',
        confirmPassword: 'Password1',
      );

      await tester.tap(find.text('注册'));
      await tester.pumpAndSettle();

      expect(find.text('邮箱已被注册'), findsOneWidget);
    });

    testWidgets('navigates to login page', (tester) async {
      await pumpRegisterPage(tester);
      await tester.tap(find.text('已有账号？去登录'));
      await tester.pumpAndSettle();
      expect(find.byType(LoginPage), findsOneWidget);
    });
  });
}
