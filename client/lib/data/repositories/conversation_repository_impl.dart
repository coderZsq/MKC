import '../../../domain/entities/conversation.dart';
import '../../../domain/repositories/conversation_repository.dart';
import '../../../shared/result.dart';
import '../datasources/remote/chat_api.dart';

/// Coordinates conversation list, creation, and deletion API calls.
class ConversationRepositoryImpl implements ConversationRepository {
  ConversationRepositoryImpl({required ChatApi chatApi}) : _chatApi = chatApi;

  final ChatApi _chatApi;

  @override
  Future<Result<List<Conversation>>> listConversations() async {
    final result = await _chatApi.listConversations();
    return result.when(
      success: (models) => Result.success(
        models.map((model) => model.toDomain()).toList(),
      ),
      failure: (error) => Result<List<Conversation>>.failure(error),
    );
  }

  @override
  Future<Result<Conversation>> createConversation({
    String? title,
    List<String>? resourceIds,
  }) async {
    final result = await _chatApi.createConversation(
      title: title,
      resourceIds: resourceIds,
    );
    return result.when(
      success: (model) => Result.success(model.toDomain()),
      failure: (error) => Result<Conversation>.failure(error),
    );
  }

  @override
  Future<Result<void>> deleteConversation(String conversationId) async {
    final result = await _chatApi.deleteConversation(conversationId);
    return result.when(
      success: (_) => const Result<void>.success(null),
      failure: (error) => Result<void>.failure(error),
    );
  }
}
