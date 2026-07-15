import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/chat_event.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/chat_test_helpers.dart';

void main() {
  late FakeChatRepository repository;
  late ChatNotifier notifier;

  setUp(() {
    repository = FakeChatRepository();
    notifier = ChatNotifier(
      conversationId: 'conv-1',
      repository: repository,
    );
  });

  tearDown(() {
    notifier.dispose();
    repository.close();
  });

  group('loadMessages', () {
    test('sets messages and clears loading on success', () async {
      final messages = [
        createMessage(id: 'm1', role: MessageRole.user, content: 'Hi'),
        createMessage(id: 'm2', role: MessageRole.assistant, content: 'Hello'),
      ];
      repository.nextMessagesResult = Result.success(messages);

      await notifier.loadMessages();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.messages, hasLength(2));
      expect(notifier.state.messages.first.id, 'm1');
      expect(repository.lastConversationId, 'conv-1');
    });

    test('syncs loaded message markers with citation indexes', () async {
      repository.nextMessagesResult = Result.success([
        Message.assistant(
          id: 'm2',
          conversationId: 'conv-1',
          content: 'Answer [^3]',
          reasoning: 'Thinking [^3]',
          citations: const [
            Citation(
              resourceId: 'res-1',
              resourceName: 'doc.pdf',
              index: 1,
              originalIndex: 3,
              score: 0.9,
            ),
          ],
        ),
      ]);

      await notifier.loadMessages();

      expect(notifier.state.messages.single.content, 'Answer [^1]');
      expect(notifier.state.messages.single.reasoning, 'Thinking [^1]');
    });

    test('sets error on failure', () async {
      repository.nextMessagesResult = const Result.failure(NetworkException());

      await notifier.loadMessages();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, isA<NetworkException>());
      expect(notifier.state.messages, isEmpty);
    });
  });

  group('send', () {
    test('appends user message and starts streaming assistant message',
        () async {
      repository.events = const [];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      expect(notifier.state.isSending, isFalse);
      expect(notifier.state.messages, hasLength(2));
      expect(notifier.state.messages[0].role, MessageRole.user);
      expect(notifier.state.messages[0].content, 'Question');
      expect(notifier.state.messages[1].role, MessageRole.assistant);
      expect(repository.lastQuestion, 'Question');
    });

    test('appends chunks to the streaming assistant message', () async {
      repository.events = const [
        ChatEvent(type: 'chunk', messageId: 'a1', delta: 'First '),
        ChatEvent(type: 'chunk', messageId: 'a1', delta: 'answer'),
      ];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      expect(notifier.state.messages, hasLength(2));
      expect(notifier.state.messages[1].content, 'First answer');
      expect(notifier.state.messages[1].isStreaming, isFalse);
    });

    test('appends reasoning to the streaming assistant message', () async {
      repository.events = const [
        ChatEvent(
          type: 'reasoning',
          messageId: 'a1',
          reasoningDelta: 'thinking ',
        ),
        ChatEvent(
          type: 'reasoning',
          messageId: 'a1',
          reasoningDelta: 'step',
        ),
        ChatEvent(type: 'chunk', messageId: 'a1', delta: 'answer'),
      ];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      expect(notifier.state.messages, hasLength(2));
      expect(notifier.state.messages[1].reasoning, 'thinking step');
      expect(notifier.state.messages[1].content, 'answer');
    });

    test('appends citation to assistant message', () async {
      repository.events = const [
        ChatEvent(
          type: 'citation',
          messageId: 'a1',
          citation: CitationData(
            resourceId: 'res-1',
            index: 1,
            chunkId: 'chunk-1',
            resourceName: 'doc.pdf',
            score: 0.9,
            page: '4',
            snippet: 'source',
            contentType: 'pdf',
          ),
        ),
      ];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      final assistant = notifier.state.messages[1];
      expect(assistant.citations, hasLength(1));
      expect(assistant.citations.first.resourceId, 'res-1');
      expect(assistant.citations.first.index, 1);
      expect(assistant.citations.first.chunkId, 'chunk-1');
      expect(assistant.citations.first.page, '4');
      expect(assistant.citations.first.snippet, 'source');
      expect(assistant.citations.first.contentType.name, 'pdf');
    });

    test('syncs streamed answer and reasoning markers with citation indexes',
        () async {
      repository.events = const [
        ChatEvent(
          type: 'reasoning',
          messageId: 'a1',
          reasoningDelta: 'thinking [^3]',
        ),
        ChatEvent(type: 'chunk', messageId: 'a1', delta: 'answer [^3]'),
        ChatEvent(
          type: 'citation',
          messageId: 'a1',
          citation: CitationData(
            resourceId: 'res-1',
            index: 1,
            originalIndex: 3,
            resourceName: 'doc.pdf',
            score: 0.9,
            page: '4',
            contentType: 'pdf',
          ),
        ),
      ];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      final assistant = notifier.state.messages[1];
      expect(assistant.reasoning, 'thinking [^1]');
      expect(assistant.content, 'answer [^1]');
      expect(assistant.citations.first.index, 1);
    });

    test('sets error on SSE error event', () async {
      repository.events = const [
        ChatEvent(type: 'error', messageId: 'a1', errorCode: '500'),
      ];

      await notifier.send('Question');
      await Future.delayed(Duration.zero);

      expect(notifier.state.isSending, isFalse);
      expect(notifier.state.error, isA<ServerException>());
    });

    test('does not send when already streaming', () async {
      repository
        ..keepOpen = true
        ..events = const [
          ChatEvent(type: 'chunk', messageId: 'a1', delta: 'Partial'),
        ];
      await notifier.send('First');
      await Future.delayed(Duration.zero);
      expect(notifier.state.isSending, isTrue);
      expect(notifier.state.messages, hasLength(2));

      await notifier.send('Second');
      // Should not append because already sending
      expect(notifier.state.messages, hasLength(2));
      expect(repository.lastQuestion, 'First');
    });
  });

  group('cancel', () {
    test('stops streaming and resets sending flag', () async {
      repository
        ..keepOpen = true
        ..events = const [
          ChatEvent(type: 'chunk', messageId: 'a1', delta: 'Partial'),
        ];
      await notifier.send('Question');
      await Future.delayed(Duration.zero);
      expect(notifier.state.isSending, isTrue);

      notifier.cancel();

      expect(notifier.state.isSending, isFalse);
      expect(notifier.state.messages[1].isStreaming, isFalse);
    });
  });
}
