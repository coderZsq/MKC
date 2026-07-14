import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mkc_client/app.dart';
import 'package:mkc_client/domain/entities/chat_event.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/conversation.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/domain/entities/parsed_page.dart';
import 'package:mkc_client/domain/entities/subtitle_segment.dart';
import 'package:mkc_client/domain/repositories/chat_repository.dart';
import 'package:mkc_client/domain/repositories/content_repository.dart';
import 'package:mkc_client/domain/repositories/conversation_repository.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/presentation/providers/app_provider.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/presentation/providers/content_view_provider.dart';
import 'package:mkc_client/presentation/providers/conversation_list_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

/// Citation click-to-content E2E test on Chrome.
///
/// Covers: assistant message with citation -> CitationCard renders -> tap
/// navigates to /resources/:id/content -> ContentViewPage loads and displays
/// the result -> back returns to the chat.
///
/// All non-deterministic boundaries (auth, chat SSE, content API) are injected
/// with fakes so the test does not depend on Gateway/AI Service.
///
/// Intended for Chrome via:
///   flutter drive --driver=test_driver/integration_test.dart \
///     --target=integration_test/citation_click_e2e_test.dart -d chrome
/// Can also run headless with:
///   flutter test integration_test/citation_click_e2e_test.dart -d flutter-tester
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  const fakeAccessToken = 'e2e-fake-access-token';

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
    required ContentRepository contentRepository,
  }) {
    return ProviderScope(
      key: UniqueKey(),
      overrides: [
        tokenProvider.overrideWithValue(const FakeTokenProvider(fakeAccessToken)),
        conversationRepositoryProvider.overrideWithValue(conversationRepository),
        chatRepositoryProvider.overrideWithValue(chatRepository),
        contentRepositoryProvider.overrideWithValue(contentRepository),
      ],
      child: const MKCApp(),
    );
  }

  group('Citation click-to-content E2E on Chrome', () {
    testWidgets(
      'tapping a PDF citation from history navigates to content view and back',
      (WidgetTester tester) async {
        const resourceId = 'res-citation-pdf';
        const resourceName = 'Q1 Report PDF';
        final conversations = FakeConversationRepository()
          ..seed([_conversation(id: 'conv-citation', title: 'Citation test')]);
        final chat = FakeChatRepository()
          ..setMessages('conv-citation', [
            Message.user(
              conversationId: 'conv-citation',
              content: 'What does the report say?',
            ),
            Message.assistant(
              conversationId: 'conv-citation',
              content: 'The report highlights key metrics.',
              citations: const [
                Citation(
                  resourceId: resourceId,
                  resourceName: resourceName,
                  score: 0.91,
                  contentType: ContentType.pdf,
                ),
              ],
            ),
          ]);
        final content = FakeContentRepository()
          ..setContent(
            resourceId,
            ContentType.pdf,
            const PdfContent(
              taskId: 'task-pdf-1',
              pages: [
                ParsedPage(
                  pageNumber: 1,
                  text: 'Revenue grew by 42% in Q1.',
                ),
              ],
            ),
          );

        await tester.pumpWidget(authenticatedApp(
          conversationRepository: conversations,
          chatRepository: chat,
          contentRepository: content,
        ));
        await pumpUntilPage(tester, '首页占位 — 功能开发中');

        currentRouter(tester).go('/conversation/conv-citation');
        await pumpUntilPage(tester, 'Chat');

        expect(find.text(resourceName), findsOneWidget);

        await tester.tap(find.text(resourceName));
        await pumpUntilPage(tester, 'PDF 文本');

        expect(find.text('第 1 页'), findsOneWidget);
        expect(find.text('Revenue grew by 42% in Q1.'), findsOneWidget);

        currentRouter(tester).pop();
        await pumpUntilPage(tester, 'Chat');
        expect(find.text(resourceName), findsOneWidget);
      },
    );

    testWidgets(
      'citation streamed with resource_type navigates to audio content view',
      (WidgetTester tester) async {
        const resourceId = 'res-citation-audio';
        const resourceName = 'All Hands Recording';
        final conversations = FakeConversationRepository()
          ..seed([_conversation(id: 'conv-stream', title: 'Stream test')]);
        final chat = FakeChatRepository()
          ..setStreamForConversation(
            'conv-stream',
            Stream.fromIterable([
              const ChatEvent(
                type: 'chunk',
                messageId: 'msg-stream',
                conversationId: 'conv-stream',
                delta: 'Here is the relevant part.',
              ),
              const ChatEvent(
                type: 'citation',
                messageId: 'msg-stream',
                conversationId: 'conv-stream',
                citation: CitationData(
                  resourceId: resourceId,
                  resourceName: resourceName,
                  score: 0.88,
                  contentType: 'audio',
                ),
              ),
              const ChatEvent(
                type: 'done',
                messageId: 'msg-stream',
                conversationId: 'conv-stream',
              ),
            ]),
          );
        final content = FakeContentRepository()
          ..setContent(
            resourceId,
            ContentType.audio,
            const AudioContent(
              taskId: 'task-audio-1',
              segments: [
                SubtitleSegment(
                  index: 1,
                  start: Duration(seconds: 5),
                  end: Duration(seconds: 10),
                  text: 'Welcome to the all hands meeting.',
                ),
              ],
            ),
          );

        await tester.pumpWidget(authenticatedApp(
          conversationRepository: conversations,
          chatRepository: chat,
          contentRepository: content,
        ));
        await pumpUntilPage(tester, '首页占位 — 功能开发中');

        currentRouter(tester).go('/conversation/conv-stream');
        await pumpUntilPage(tester, 'Chat');

        await tester.enterText(find.byType(TextField), 'Summarize the meeting');
        await tester.tap(find.byIcon(Icons.send));
        await tester.pumpAndSettle();

        await pumpUntilFound(tester, find.text(resourceName));
        expect(find.text(resourceName), findsOneWidget);

        await tester.tap(find.text(resourceName));
        await pumpUntilPage(tester, '音频字幕');

        expect(find.text('Welcome to the all hands meeting.'), findsOneWidget);
      },
    );

    testWidgets(
      'tapping a citation with no content shows an error that can be retried',
      (WidgetTester tester) async {
        const resourceId = 'res-citation-missing';
        const resourceName = 'Missing Content';
        final conversations = FakeConversationRepository()
          ..seed([_conversation(id: 'conv-error', title: 'Error test')]);
        final chat = FakeChatRepository()
          ..setMessages('conv-error', [
            Message.assistant(
              conversationId: 'conv-error',
              content: 'See the source.',
              citations: const [
                Citation(
                  resourceId: resourceId,
                  resourceName: resourceName,
                  score: 0.5,
                  contentType: ContentType.pdf,
                ),
              ],
            ),
          ]);
        final content = FakeContentRepository()
          ..setError(resourceId, ContentType.pdf, const ServerException());

        await tester.pumpWidget(authenticatedApp(
          conversationRepository: conversations,
          chatRepository: chat,
          contentRepository: content,
        ));
        await pumpUntilPage(tester, '首页占位 — 功能开发中');

        currentRouter(tester).go('/conversation/conv-error');
        await pumpUntilPage(tester, 'Chat');

        await tester.tap(find.text(resourceName));
        await pumpUntilPage(tester, '内容查看');

        expect(find.text('服务器内部错误'), findsOneWidget);
        expect(find.text('重试'), findsOneWidget);
      },
    );
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
  final Map<String, Stream<ChatEvent>> _streams = {};

  void setMessages(String conversationId, List<Message> messages) {
    _messages[conversationId] = messages;
  }

  void setStreamForConversation(
    String conversationId,
    Stream<ChatEvent> stream,
  ) {
    _streams[conversationId] = stream;
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
    return _streams[conversationId] ??
        Stream.fromIterable([
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

class FakeContentRepository implements ContentRepository {
  final Map<String, Content> _content = {};
  final Map<String, AppException> _errors = {};

  void setContent(String resourceId, ContentType type, Content content) {
    _content['$resourceId:${type.name}'] = content;
  }

  void setError(String resourceId, ContentType type, AppException error) {
    _errors['$resourceId:${type.name}'] = error;
  }

  @override
  Future<Result<Content>> getContent(
    String resourceId,
    ContentType contentType,
  ) async {
    final key = '$resourceId:${contentType.name}';
    final error = _errors[key];
    if (error != null) {
      return Result<Content>.failure(error);
    }
    final content = _content[key];
    if (content != null) {
      return Result<Content>.success(content);
    }
    return const Result<Content>.failure(
      ServerException(code: 'NOT_FOUND'),
    );
  }
}
