import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/data/datasources/secure/secure_token_storage.dart';
import 'package:mkc_client/domain/entities/chat_event.dart';
import 'package:mkc_client/domain/entities/conversation.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/domain/repositories/chat_repository.dart';
import 'package:mkc_client/domain/repositories/conversation_repository.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/presentation/providers/app_provider.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/presentation/providers/conversation_list_provider.dart';
import 'package:mkc_client/presentation/routes/app_routes.dart';
import 'package:mkc_client/shared/result.dart';

/// S3-8 会话持久化 Chrome E2E 测试。
///
/// 覆盖：会话列表页、创建会话、删除会话（含二次确认）、消息查看。
/// 对非确定性边界（API、SSE）注入 Fake，使测试不依赖 Gateway/AI Service。
///
/// 执行命令：
/// flutter test integration_test/s3_8_conversation_e2e_test.dart -d chrome
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  const fakeAccessToken = 'e2e-fake-access-token';
  final storage = SecureTokenStorage();

  Future<void> pumpUntilFound(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 5),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(const Duration(milliseconds: 100));
      if (finder.evaluate().isNotEmpty) return;
    }
    throw Exception('Timed out waiting for $finder');
  }

  Future<void> pumpUntilPage(WidgetTester tester, String title) async {
    await pumpUntilFound(tester, find.text(title));
    await tester.pumpAndSettle();
  }

  GoRouter currentRouter(WidgetTester tester) {
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    return app.routerConfig as GoRouter;
  }

  Widget authenticatedApp({
    required ConversationRepository conversationRepository,
    required ChatRepository chatRepository,
  }) {
    return ProviderScope(
      key: UniqueKey(),
      overrides: [
        tokenProvider.overrideWithValue(
          const FakeTokenProvider(fakeAccessToken),
        ),
        conversationRepositoryProvider.overrideWithValue(
          conversationRepository,
        ),
        chatRepositoryProvider.overrideWithValue(chatRepository),
      ],
      child: const MKCApp(),
    );
  }

  setUp(() async {
    await storage.clearTokens();
  });

  group('S3-8 conversation persistence E2E on Chrome', () {
    testWidgets('unauthenticated user is redirected to login', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(key: UniqueKey(), child: const MKCApp()),
      );
      await pumpUntilPage(tester, '登录 MKC');

      currentRouter(tester).go(conversationListRoute);
      await tester.pumpAndSettle();

      expect(find.text('Conversations'), findsNothing);
      expect(find.text('登录 MKC'), findsOneWidget);
    });

    testWidgets('conversation list shows empty state', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository();
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(conversationListRoute);
      await pumpUntilPage(tester, 'Conversations');

      expect(find.text('No conversations yet'), findsOneWidget);
      expect(find.text('Start a new conversation'), findsOneWidget);
    });

    testWidgets('create conversation from empty state navigates to chat', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository();
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(conversationListRoute);
      await pumpUntilPage(tester, 'Conversations');

      await tester.tap(find.text('Start a new conversation'));
      await pumpUntilPage(tester, 'Chat');

      expect(conversations.conversations.length, 1);
      expect(conversations.conversations.first.title, 'Untitled conversation');
      expect(find.text('Send a message to start the conversation'), findsOneWidget);
    });

    testWidgets('create conversation from app bar navigates to chat', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository();
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(conversationListRoute);
      await pumpUntilPage(tester, 'Conversations');

      await tester.tap(find.byIcon(Icons.add));
      await pumpUntilPage(tester, 'Chat');

      expect(conversations.conversations.length, 1);
    });

    testWidgets('conversation list displays existing conversations', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository()
        ..seed([
          _conversation(id: 'conv-1', title: 'Project retro'),
          _conversation(id: 'conv-2', title: 'Q3 planning'),
        ]);
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(conversationListRoute);
      await pumpUntilPage(tester, 'Conversations');

      expect(find.text('Project retro'), findsOneWidget);
      expect(find.text('Q3 planning'), findsOneWidget);
      expect(find.byType(ListTile), findsNWidgets(2));
    });

    testWidgets('delete conversation shows confirmation and removes it', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository()
        ..seed([
          _conversation(id: 'conv-1', title: 'Keep me'),
          _conversation(id: 'conv-2', title: 'Delete me'),
        ]);
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go(conversationListRoute);
      await pumpUntilPage(tester, 'Conversations');

      await tester.tap(find.byIcon(Icons.delete_outline).at(1));
      await tester.pumpAndSettle();

      expect(find.text('Delete conversation'), findsOneWidget);
      expect(
        find.text('Are you sure you want to delete this conversation?'),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Delete'), findsOneWidget);

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Delete conversation'), findsNothing);
      expect(find.text('Keep me'), findsOneWidget);
      expect(find.text('Delete me'), findsOneWidget);

      await tester.tap(find.byIcon(Icons.delete_outline).at(1));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete'));
      await pumpUntilFound(tester, find.text('Keep me'));

      expect(find.text('Keep me'), findsOneWidget);
      expect(find.text('Delete me'), findsNothing);
      expect(conversations.conversations.length, 1);
    });

    testWidgets('chat page displays historical messages', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository()
        ..seed([_conversation(id: 'conv-history', title: 'History')]);
      final chat = FakeChatRepository()
        ..setMessages('conv-history', [
          Message.user(
            conversationId: 'conv-history',
            content: 'Hello assistant',
          ),
          Message.assistant(
            conversationId: 'conv-history',
            content: 'Hello user',
          ),
        ]);

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go('/conversation/conv-history');
      await pumpUntilPage(tester, 'Chat');

      expect(find.text('Hello assistant'), findsOneWidget);
      expect(find.text('Hello user'), findsOneWidget);
    });

    testWidgets('sending a question streams deterministic answer', (
      WidgetTester tester,
    ) async {
      final conversations = FakeConversationRepository()
        ..seed([_conversation(id: 'conv-stream', title: 'Stream')]);
      final chat = FakeChatRepository();

      await tester.pumpWidget(authenticatedApp(
        conversationRepository: conversations,
        chatRepository: chat,
      ));
      await pumpUntilPage(tester, '首页占位 — 功能开发中');

      currentRouter(tester).go('/conversation/conv-stream');
      await pumpUntilPage(tester, 'Chat');

      await tester.enterText(find.byType(TextField), 'What is MKC?');
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();

      expect(find.text('What is MKC?'), findsOneWidget);

      await pumpUntilFound(tester, find.text('This is a deterministic answer.'));
      expect(find.text('This is a deterministic answer.'), findsOneWidget);
      expect(find.byIcon(Icons.send), findsOneWidget);
    });
  });
}

Conversation _conversation({required String id, required String title}) {
  final now = DateTime.now();
  return Conversation(
    id: id,
    title: title,
    createdAt: now,
    updatedAt: now,
  );
}

class FakeTokenProvider implements TokenProvider {
  const FakeTokenProvider(this.accessToken);

  final String accessToken;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {}
}

class FakeConversationRepository implements ConversationRepository {
  final List<Conversation> _conversations = [];

  List<Conversation> get conversations => List.unmodifiable(_conversations);

  void seed(List<Conversation> items) {
    _conversations
      ..clear()
      ..addAll(items);
  }

  @override
  Future<Result<List<Conversation>>> listConversations() async {
    return Result.success(List.unmodifiable(_conversations));
  }

  @override
  Future<Result<Conversation>> createConversation({
    String? title,
    List<String>? resourceIds,
  }) async {
    final now = DateTime.now();
    final conversation = Conversation(
      id: 'conv-${now.millisecondsSinceEpoch}',
      title: title ?? 'Untitled conversation',
      resourceIds: resourceIds ?? const <String>[],
      createdAt: now,
      updatedAt: now,
    );
    _conversations.insert(0, conversation);
    return Result.success(conversation);
  }

  @override
  Future<Result<void>> deleteConversation(String conversationId) async {
    _conversations.removeWhere((c) => c.id == conversationId);
    return const Result.success(null);
  }
}

class FakeChatRepository implements ChatRepository {
  final Map<String, List<Message>> _messages = {};

  void setMessages(String conversationId, List<Message> messages) {
    _messages[conversationId] = messages;
  }

  @override
  Future<Result<List<Message>>> loadMessages(
    String conversationId, {
    int? page,
    int? limit,
  }) async {
    return Result.success(List.unmodifiable(_messages[conversationId] ?? []));
  }

  @override
  Stream<ChatEvent> sendQuestion(String conversationId, String question) {
    return Stream.fromIterable([
      ChatEvent(
        type: 'chunk',
        messageId: 'msg-$conversationId',
        conversationId: conversationId,
        delta: 'This is a deterministic answer.',
      ),
      ChatEvent(
        type: 'done',
        messageId: 'msg-$conversationId',
        conversationId: conversationId,
      ),
    ]);
  }
}
