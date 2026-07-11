import 'dart:async';

import 'package:mkc_client/domain/entities/chat_event.dart';
import 'package:mkc_client/domain/entities/conversation.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/domain/repositories/chat_repository.dart';
import 'package:mkc_client/domain/repositories/conversation_repository.dart';
import 'package:mkc_client/shared/result.dart';

Message createMessage({
  String id = 'msg-1',
  String conversationId = 'conv-1',
  MessageRole role = MessageRole.user,
  String content = 'Hello',
  List<Citation> citations = const <Citation>[],
  DateTime? createdAt,
  bool isStreaming = false,
}) {
  return Message(
    id: id,
    conversationId: conversationId,
    role: role,
    content: content,
    citations: citations,
    createdAt: createdAt ?? DateTime(2024, 1, 1, 12, 0),
    isStreaming: isStreaming,
  );
}

Conversation makeConversation({
  String id = 'conv-1',
  String title = 'Test conversation',
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  return Conversation(
    id: id,
    title: title,
    createdAt: createdAt ?? DateTime(2024, 1, 1, 12, 0),
    updatedAt: updatedAt ?? DateTime(2024, 1, 1, 12, 0),
  );
}

class FakeChatRepository implements ChatRepository {
  Result<List<Message>>? nextMessagesResult;
  List<ChatEvent> events = const <ChatEvent>[];
  bool keepOpen = false;
  StreamController<ChatEvent>? _controller;
  String? lastConversationId;
  String? lastQuestion;

  @override
  Future<Result<List<Message>>> loadMessages(String conversationId) async {
    lastConversationId = conversationId;
    return nextMessagesResult ?? const Result.success([]);
  }

  @override
  Stream<ChatEvent> sendQuestion(String conversationId, String question) {
    lastConversationId = conversationId;
    lastQuestion = question;
    if (keepOpen) {
      _controller = StreamController<ChatEvent>();
      for (final event in events) {
        _controller!.add(event);
      }
      return _controller!.stream;
    }
    return Stream.fromIterable(events);
  }

  void close() {
    _controller?.close();
    _controller = null;
  }
}

class FakeConversationRepository implements ConversationRepository {
  Result<List<Conversation>>? nextListResult;
  Result<Conversation>? nextCreateResult;
  Result<void>? nextDeleteResult;
  String? lastDeletedId;
  int createCalls = 0;
  int listCalls = 0;
  int deleteCalls = 0;

  @override
  Future<Result<List<Conversation>>> listConversations() async {
    listCalls++;
    return nextListResult ?? const Result.success([]);
  }

  @override
  Future<Result<Conversation>> createConversation() async {
    createCalls++;
    return nextCreateResult ?? Result.success(makeConversation(id: 'new-conv'));
  }

  @override
  Future<Result<void>> deleteConversation(String conversationId) async {
    deleteCalls++;
    lastDeletedId = conversationId;
    return nextDeleteResult ?? const Result.success(null);
  }
}
