import 'dart:html';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/data/datasources/secure/secure_token_storage.dart';

/// Chrome 全链路 E2E 测试：Flutter Web → Gateway API → MySQL/Redis。
///
/// 运行前请确保：
/// - K8s 端口转发已启动（MySQL 3306 / Redis 6379）。
/// - Gateway 已启动并监听 8080（BASE_URL 指向 localhost:8080/api/v1）。
/// - chromedriver 在 4444 端口运行。
///
/// 执行命令：
/// flutter drive --driver=test_driver/integration_test.dart \
///   --target=integration_test/auth_e2e_test.dart -d chrome \
///   --dart-define=BASE_URL=http://localhost:8080/api/v1
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final storage = SecureTokenStorage();

  String uniqueEmail(String suffix) {
    return 'e2e_${DateTime.now().millisecondsSinceEpoch}_$suffix@example.com';
  }

  /// 循环 pump 直到 [finder] 出现，避免 CircularProgressIndicator 导致 pumpAndSettle 超时。
  Future<void> pumpUntilFound(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(const Duration(milliseconds: 200));
      if (finder.evaluate().isNotEmpty) return;
    }
    throw Exception('Timed out waiting for $finder');
  }

  /// 等待页面标题出现，并让页面转场动画结束。
  Future<void> pumpUntilPage(
    WidgetTester tester,
    String title,
  ) async {
    await pumpUntilFound(tester, find.text(title));
    await tester.pumpAndSettle();
  }

  Finder submitButton(String text) => find.widgetWithText(ElevatedButton, text);

  Future<void> enterEmail(WidgetTester tester, String email) async {
    await tester.enterText(
      find.widgetWithText(TextFormField, '邮箱'),
      email,
    );
  }

  Future<void> enterPassword(WidgetTester tester, String password) async {
    await tester.enterText(
      find.widgetWithText(TextFormField, '密码'),
      password,
    );
  }

  Future<void> enterConfirmPassword(
    WidgetTester tester,
    String password,
  ) async {
    await tester.enterText(
      find.widgetWithText(TextFormField, '确认密码'),
      password,
    );
  }

  Future<void> enterNickname(
    WidgetTester tester,
    String nickname,
  ) async {
    await tester.enterText(
      find.widgetWithText(TextFormField, '昵称（可选）'),
      nickname,
    );
  }

  group('Auth full-link E2E on Chrome', () {
    setUp(() async {
      await storage.clearTokens();
      window.localStorage.clear();
    });

    testWidgets('navigates from splash to login when unauthenticated', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      expect(submitButton('登录'), findsOneWidget);
    });

    testWidgets('navigates between login and register pages', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');

      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');
      expect(submitButton('注册'), findsOneWidget);

      await tester.tap(find.text('已有账号？去登录'));
      await pumpUntilPage(tester, '登录 MKC');
      expect(submitButton('登录'), findsOneWidget);
    });

    testWidgets('shows validation errors for empty/invalid fields', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');

      await tester.tap(submitButton('登录'));
      await tester.pumpAndSettle();

      expect(find.text('请输入邮箱'), findsWidgets);
      expect(find.text('密码至少 8 位'), findsWidgets);

      await enterEmail(tester, 'not-an-email');
      await enterPassword(tester, 'short1');
      await tester.tap(submitButton('登录'));
      await tester.pumpAndSettle();

      expect(find.text('邮箱格式不正确'), findsOneWidget);
      expect(find.text('密码至少 8 位'), findsOneWidget);
    });

    testWidgets('successful registration persists token and redirects home', (
      WidgetTester tester,
    ) async {
      final email = uniqueEmail('reg');
      const password = 'Password123';

      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');

      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');

      await enterEmail(tester, email);
      await enterNickname(tester, 'E2E User');
      await enterPassword(tester, password);
      await enterConfirmPassword(tester, password);

      await tester.tap(submitButton('注册'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      final token = await storage.getAccessToken();
      expect(token, isNotNull);
      expect(token!.isNotEmpty, isTrue);
    });

    testWidgets('duplicate registration shows conflict error', (
      WidgetTester tester,
    ) async {
      final email = uniqueEmail('dup');
      const password = 'Password123';

      // 第一次注册
      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, password);
      await enterConfirmPassword(tester, password);
      await tester.tap(submitButton('注册'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      // 在同一浏览器会话中保留 token，手动登出以回到未登录状态。
      await storage.clearTokens();
      window.localStorage.clear();

      // 模拟应用冷启动：使用新的 ProviderScope 让 Riverpod 容器重建，避免旧状态残留。
      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '登录 MKC');
      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, password);
      await enterConfirmPassword(tester, password);
      await tester.tap(submitButton('注册'));
      await pumpUntilFound(tester, find.text('邮箱已被注册'));

      expect(find.text('邮箱已被注册'), findsOneWidget);
    });

    testWidgets('successful login persists token and redirects home', (
      WidgetTester tester,
    ) async {
      final email = uniqueEmail('login');
      const password = 'Password123';

      // 先通过 API 注册账号
      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, password);
      await enterConfirmPassword(tester, password);
      await tester.tap(submitButton('注册'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      await storage.clearTokens();
      window.localStorage.clear();

      // 使用相同账号登录
      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '登录 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, password);
      await tester.tap(submitButton('登录'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      final token = await storage.getAccessToken();
      expect(token, isNotNull);
      expect(token!.isNotEmpty, isTrue);
    });

    testWidgets('invalid login shows unauthorized error', (
      WidgetTester tester,
    ) async {
      final email = uniqueEmail('bad');

      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, 'WrongPass123');
      await tester.tap(submitButton('登录'));
      await pumpUntilFound(tester, find.text('邮箱或密码错误'));

      expect(find.text('邮箱或密码错误'), findsOneWidget);
    });

    testWidgets('token persistence redirects to home on app restart', (
      WidgetTester tester,
    ) async {
      final email = uniqueEmail('persist');
      const password = 'Password123';

      await tester.pumpWidget(const ProviderScope(child: MKCApp()));
      await pumpUntilPage(tester, '登录 MKC');
      await tester.tap(find.text('还没有账号？去注册'));
      await pumpUntilPage(tester, '注册 MKC');
      await enterEmail(tester, email);
      await enterPassword(tester, password);
      await enterConfirmPassword(tester, password);
      await tester.tap(submitButton('注册'));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      // 模拟应用重启：重新 pump App（新容器），保留 storage 中的 token。
      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '首页占位 — 功能开发中');
      expect(find.text('登录 MKC'), findsNothing);
    });
  });
}
