import '../entities/chat_event.dart';
import '../entities/message.dart';
import '../../shared/result.dart';

/// Repository for chat message operations.
abstract class ChatRepository {
  /// Loads historical messages for [conversationId].
  Future<Result<List<Message>>> loadMessages(
    String conversationId, {
    int? page,
    int? limit,
  });

  /// Streams assistant answer events for a new question in [conversationId].
  Stream<ChatEvent> sendQuestion(String conversationId, String question);
}
