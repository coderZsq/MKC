import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositories/conversation_repository_impl.dart';
import '../../domain/entities/conversation.dart';
import '../../domain/repositories/conversation_repository.dart';
import '../../shared/errors/app_exception.dart';
import 'chat_provider.dart';

/// UI state for the conversation list.
class ConversationListState {
  const ConversationListState({
    this.conversations = const <Conversation>[],
    this.isLoading = false,
    this.error,
    this.selectedId,
  });

  final List<Conversation> conversations;
  final bool isLoading;
  final AppException? error;
  final String? selectedId;

  ConversationListState copyWith({
    List<Conversation>? conversations,
    bool? isLoading,
    AppException? error,
    String? selectedId,
  }) {
    return ConversationListState(
      conversations: conversations ?? this.conversations,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      selectedId: selectedId ?? this.selectedId,
    );
  }
}

/// Manages conversation list state including create, delete and selection.
class ConversationListNotifier
    extends StateNotifier<ConversationListState> {
  ConversationListNotifier({required ConversationRepository repository})
      : _repository = repository,
        super(const ConversationListState());

  final ConversationRepository _repository;

  Future<void> loadConversations() async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repository.listConversations();
    state = result.when(
      success: (conversations) => state.copyWith(
        isLoading: false,
        conversations: conversations,
      ),
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  Future<Conversation?> createConversation({
    String? title,
    List<String>? resourceIds,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repository.createConversation(
      title: title,
      resourceIds: resourceIds,
    );
    return result.when(
      success: (conversation) {
        final updated = <Conversation>[conversation, ...state.conversations];
        state = state.copyWith(
          isLoading: false,
          conversations: updated,
          selectedId: conversation.id,
        );
        return conversation;
      },
      failure: (error) {
        state = state.copyWith(isLoading: false, error: error);
        return null;
      },
    );
  }

  Future<void> deleteConversation(String id) async {
    final previous = state.conversations;
    final filtered = previous.where((c) => c.id != id).toList();
    state = state.copyWith(conversations: filtered);

    final result = await _repository.deleteConversation(id);
    result.when(
      success: (_) {},
      failure: (error) {
        state = state.copyWith(
          conversations: previous,
          error: error,
        );
      },
    );
  }

  void selectConversation(String id) {
    state = state.copyWith(selectedId: id);
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

final conversationRepositoryProvider = Provider<ConversationRepository>((ref) {
  return ConversationRepositoryImpl(
    chatApi: ref.watch(chatApiProvider),
  );
});

final conversationListProvider = StateNotifierProvider.autoDispose
    <ConversationListNotifier, ConversationListState>((ref) {
  final notifier = ConversationListNotifier(
    repository: ref.watch(conversationRepositoryProvider),
  );
  notifier.loadConversations();
  return notifier;
});
