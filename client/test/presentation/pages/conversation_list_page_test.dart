import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mkc_client/presentation/pages/chat_page.dart';
import 'package:mkc_client/presentation/pages/conversation_list_page.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/presentation/providers/conversation_list_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/chat_test_helpers.dart';

void main() {
  group('ConversationListPage', () {
    testWidgets('renders conversation list', (tester) async {
      final repository = FakeConversationRepository()
        ..nextListResult = Result.success([
          makeConversation(id: 'c1', title: 'First'),
          makeConversation(id: 'c2', title: 'Second'),
        ]);

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      expect(find.text('First'), findsOneWidget);
      expect(find.text('Second'), findsOneWidget);
    });

    testWidgets('formats updated time with intl', (tester) async {
      final updatedAt = DateTime(2024, 1, 1, 12, 30);
      final repository = FakeConversationRepository()
        ..nextListResult = Result.success([
          makeConversation(id: 'c1', title: 'Timed', updatedAt: updatedAt),
        ]);

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      expect(find.text('Updated 1/1/2024 12:30'), findsOneWidget);
    });

    testWidgets('creates new conversation and navigates', (tester) async {
      final repository = FakeConversationRepository()
        ..nextListResult = const Result.success([])
        ..nextCreateResult = Result.success(
          makeConversation(id: 'new', title: 'New chat'),
        );

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Start a new conversation'));
      await tester.pumpAndSettle();

      expect(find.text('Send a message to start the conversation'), findsOneWidget);
      expect(repository.createCalls, 1);
    });

    testWidgets('shows error on load failure', (tester) async {
      final repository = FakeConversationRepository()
        ..nextListResult = const Result.failure(NetworkException());

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      expect(find.text('网络连接失败，请检查网络'), findsOneWidget);
    });
  });
}

Future<void> _pumpPage(
  WidgetTester tester, {
  required FakeConversationRepository repository,
}) async {
  final chatRepository = FakeChatRepository()
    ..nextMessagesResult = const Result.success([]);
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => const ConversationListPage(),
      ),
      GoRoute(
        path: '/conversation/:id',
        builder: (_, state) => ChatPage(
          conversationId: state.pathParameters['id']!,
        ),
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        conversationRepositoryProvider.overrideWithValue(repository),
        chatRepositoryProvider.overrideWithValue(chatRepository),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
}
