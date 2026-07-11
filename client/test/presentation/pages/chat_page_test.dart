import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/chat_event.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/presentation/pages/chat_page.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/chat_test_helpers.dart';

void main() {
  group('ChatPage', () {
    testWidgets('renders messages from repository', (tester) async {
      final repository = FakeChatRepository()
        ..nextMessagesResult = Result.success([
          createMessage(role: MessageRole.user, content: 'Hi'),
          createMessage(role: MessageRole.assistant, content: 'Hello'),
        ]);

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      expect(find.text('Hi'), findsOneWidget);
      expect(find.text('Hello'), findsOneWidget);
    });

    testWidgets('sends question and shows streamed answer', (
      tester,
    ) async {
      final repository = FakeChatRepository()
        ..nextMessagesResult = const Result.success([])
        ..events = const [
          ChatEvent(type: 'chunk', messageId: 'a1', delta: 'answer'),
        ];

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Question');
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();

      expect(repository.lastQuestion, 'Question');
      expect(find.text('answer'), findsOneWidget);
    });

    testWidgets('shows error banner on load failure', (tester) async {
      final repository = FakeChatRepository()
        ..nextMessagesResult = const Result.failure(NetworkException());

      await _pumpPage(tester, repository: repository);
      await tester.pumpAndSettle();

      expect(find.text('网络连接失败，请检查网络'), findsOneWidget);
    });
  });
}

Future<void> _pumpPage(
  WidgetTester tester, {
  required FakeChatRepository repository,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        chatRepositoryProvider.overrideWithValue(repository),
      ],
      child: const MaterialApp(
        home: ChatPage(conversationId: 'conv-1'),
      ),
    ),
  );
}
