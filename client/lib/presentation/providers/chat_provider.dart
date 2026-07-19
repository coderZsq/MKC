import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/env.dart';
import '../../data/datasources/remote/chat_api.dart';
import '../../data/datasources/remote/chat_sse_client.dart';
import '../../data/repositories/chat_repository_impl.dart';
import '../../domain/entities/chat_event.dart';
import '../../domain/entities/content_type.dart';
import '../../domain/entities/message.dart';
import '../../domain/repositories/chat_repository.dart';
import '../../shared/errors/app_exception.dart';
import 'app_provider.dart';

/// UI state for a single conversation.
class ChatState {
  const ChatState({
    this.messages = const <Message>[],
    this.isLoading = false,
    this.isSending = false,
    this.error,
    this.title = '',
    this.lastQuestion,
    this.canRetryLastQuestion = false,
  });

  final List<Message> messages;
  final bool isLoading;
  final bool isSending;
  final AppException? error;
  final String title;
  final String? lastQuestion;
  final bool canRetryLastQuestion;

  ChatState copyWith({
    List<Message>? messages,
    bool? isLoading,
    bool? isSending,
    AppException? error,
    String? title,
    String? lastQuestion,
    bool? canRetryLastQuestion,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      error: error,
      title: title ?? this.title,
      lastQuestion: lastQuestion ?? this.lastQuestion,
      canRetryLastQuestion: canRetryLastQuestion ?? this.canRetryLastQuestion,
    );
  }
}

/// Manages message history, streaming answers and send/cancel lifecycle.
class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier({
    required String conversationId,
    required ChatRepository repository,
  })  : _conversationId = conversationId,
        _repository = repository,
        super(const ChatState());

  final String _conversationId;
  final ChatRepository _repository;
  StreamSubscription<ChatEvent>? _sseSubscription;

  Future<void> loadMessages() async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repository.loadMessages(_conversationId);
    state = result.when(
      success: (messages) => state.copyWith(
        isLoading: false,
        messages: messages
            .map((message) => message.withCitationMarkersSynced())
            .toList(),
      ),
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  Future<void> send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || state.isSending) return;

    _sseSubscription?.cancel();
    _sseSubscription = null;

    final userMessage = Message.user(
      conversationId: _conversationId,
      content: trimmed,
    );
    final messagesWithUser = <Message>[...state.messages, userMessage];
    state = state.copyWith(
      messages: messagesWithUser,
      isSending: true,
      error: null,
      lastQuestion: trimmed,
      canRetryLastQuestion: false,
    );

    final assistantMessage = Message.assistant(
      conversationId: _conversationId,
      isStreaming: true,
    );
    state = state.copyWith(
      messages: <Message>[...messagesWithUser, assistantMessage],
    );

    final stream = _repository.sendQuestion(_conversationId, trimmed);
    _sseSubscription = stream.listen(
      _handleEvent,
      onError: (_) => _stopStreaming(const StreamDisconnectedException()),
      onDone: () => _stopStreaming(null),
    );
  }

  Future<void> retryLastQuestion() async {
    final question = state.lastQuestion;
    if (question == null || question.trim().isEmpty || state.isSending) {
      return;
    }
    state = state.copyWith(error: null, canRetryLastQuestion: false);
    await send(question);
  }

  void cancel() {
    _sseSubscription?.cancel();
    _sseSubscription = null;
    _stopStreaming(null);
  }

  void clearError() {
    state = state.copyWith(error: null);
  }

  void _handleEvent(ChatEvent event) {
    switch (event.type) {
      case 'chunk':
        _appendChunk(event);
      case 'reasoning':
        _appendReasoning(event);
      case 'citation':
        _appendCitation(event);
      case 'done':
        _stopStreaming(null);
      case 'error':
        if (event.errorCode == 'UNAUTHORIZED') {
          _stopStreaming(const UnauthorizedException());
        } else {
          _stopStreaming(
            ServerException(
              code: event.errorCode,
              message: event.errorMessage,
              traceId: event.traceId,
              retryable: event.retryable,
            ),
          );
        }
    }
  }

  void _appendChunk(ChatEvent event) {
    final targetId = event.messageId.isNotEmpty ? event.messageId : null;
    final updated = state.messages.map((message) {
      if (!_matchesTarget(message, targetId)) return message;
      return message.copyWith(
        id: message.id.isEmpty ? event.messageId : message.id,
        content: message.content + (event.delta ?? ''),
      );
    }).toList();
    state = state.copyWith(messages: updated);
  }

  void _appendReasoning(ChatEvent event) {
    final targetId = event.messageId.isNotEmpty ? event.messageId : null;
    final updated = state.messages.map((message) {
      if (!_matchesTarget(message, targetId)) return message;
      return message.copyWith(
        id: message.id.isEmpty ? event.messageId : message.id,
        reasoning: message.reasoning + (event.reasoningDelta ?? ''),
      );
    }).toList();
    state = state.copyWith(messages: updated);
  }

  void _appendCitation(ChatEvent event) {
    final data = event.citation;
    if (data == null) return;
    final citation = Citation(
      resourceId: data.resourceId,
      resourceName: data.resourceName ?? '',
      index: data.index,
      originalIndex: data.originalIndex,
      chunkId: data.chunkId,
      page: data.page,
      timestamp: data.timestamp,
      timestampEnd: data.timestampEnd,
      snippet: data.snippet,
      score: data.score,
      contentType: ContentType.fromParam(data.contentType),
    );
    final targetId = event.messageId.isNotEmpty ? event.messageId : null;
    final updated = state.messages.map((message) {
      if (!_matchesTarget(message, targetId)) return message;
      return message.copyWith(
        id: message.id.isEmpty ? event.messageId : message.id,
        citations: <Citation>[...message.citations, citation],
      ).withCitationMarkersSynced();
    }).toList();
    state = state.copyWith(messages: updated);
  }

  bool _matchesTarget(Message message, String? targetId) {
    if (message.role != MessageRole.assistant) return false;
    if (targetId != null) return message.id == targetId || message.id.isEmpty;
    return message.isStreaming;
  }

  void _stopStreaming(AppException? error) {
    if (!state.isSending) return;
    final updated = state.messages.map((message) {
      if (message.role != MessageRole.assistant || !message.isStreaming) {
        return message;
      }
      return message.copyWith(isStreaming: false);
    }).toList();
    state = state.copyWith(
      messages: updated,
      isSending: false,
      error: error,
      canRetryLastQuestion: error is StreamDisconnectedException ||
          _isRetryableServerError(error),
    );
  }

  bool _isRetryableServerError(AppException? error) {
    return error is ServerException && error.retryable;
  }

  @override
  void dispose() {
    _sseSubscription?.cancel();
    _sseSubscription = null;
    super.dispose();
  }
}

final chatSseClientProvider = Provider<ChatSseClient>((ref) {
  return ChatSseClient(
    baseUrl: Env.baseUrl,
    tokenProvider: ref.watch(tokenProvider),
  );
});

final chatApiProvider = Provider<ChatApi>((ref) {
  return ChatApi(client: ref.watch(apiClientProvider));
});

final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  return ChatRepositoryImpl(
    chatApi: ref.watch(chatApiProvider),
    sseClient: ref.watch(chatSseClientProvider),
  );
});

final chatProvider = StateNotifierProvider.autoDispose
    .family<ChatNotifier, ChatState, String>((ref, conversationId) {
  final notifier = ChatNotifier(
    conversationId: conversationId,
    repository: ref.watch(chatRepositoryProvider),
  );
  notifier.loadMessages();
  return notifier;
});
