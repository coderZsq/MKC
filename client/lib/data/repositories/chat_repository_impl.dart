import '../../../domain/entities/chat_event.dart';
import '../../../domain/entities/message.dart';
import '../../../domain/repositories/chat_repository.dart';
import '../../../shared/result.dart';
import '../datasources/remote/chat_api.dart';
import '../datasources/remote/chat_sse_client.dart';

/// Coordinates chat message loading and streaming answer events.
class ChatRepositoryImpl implements ChatRepository {
  ChatRepositoryImpl({
    required ChatApi chatApi,
    required ChatSseClient sseClient,
  })  : _chatApi = chatApi,
        _sseClient = sseClient;

  final ChatApi _chatApi;
  final ChatSseClient _sseClient;

  @override
  Future<Result<List<Message>>> loadMessages(
    String conversationId, {
    int? page,
    int? limit,
  }) async {
    final result = await _chatApi.loadMessages(
      conversationId,
      page: page,
      limit: limit,
    );
    return result.when(
      success: (models) => Result.success(
        models
            .map(
              (model) => model.toDomain().copyWith(conversationId: conversationId),
            )
            .toList(),
      ),
      failure: (error) => Result<List<Message>>.failure(error),
    );
  }

  @override
  Stream<ChatEvent> sendQuestion(String conversationId, String question) {
    return _sseClient.ask(conversationId, question);
  }
}
