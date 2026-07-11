import '../entities/conversation.dart';
import '../../shared/result.dart';

/// Repository for conversation management operations.
abstract class ConversationRepository {
  /// Returns the list of conversations for the current user.
  Future<Result<List<Conversation>>> listConversations();

  /// Creates a new conversation and returns it.
  Future<Result<Conversation>> createConversation();

  /// Deletes the conversation with [conversationId].
  Future<Result<void>> deleteConversation(String conversationId);
}
