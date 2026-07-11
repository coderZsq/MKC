import '../../../shared/result.dart';
import '../../models/conversation_model.dart';
import '../../models/message_model.dart';
import 'api_client.dart';

/// Remote chat API endpoints.
class ChatApi {
  ChatApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  static const String _path = '/conversations';

  Future<Result<List<ConversationModel>>> listConversations() async {
    return _client.get<List<ConversationModel>>(
      _path,
      parser: (dynamic data) {
        final list = data as List<dynamic>? ?? <dynamic>[];
        return list
            .map(
              (dynamic item) => ConversationModel.fromJson(item as Map<String, dynamic>),
            )
            .toList();
      },
    );
  }

  Future<Result<ConversationModel>> createConversation() async {
    return _client.post<ConversationModel>(
      _path,
      parser: (dynamic data) => ConversationModel.fromJson(data as Map<String, dynamic>),
    );
  }

  Future<Result<List<MessageModel>>> loadMessages(String conversationId) async {
    return _client.get<List<MessageModel>>(
      '$_path/$conversationId/messages',
      parser: (dynamic data) {
        final list = data as List<dynamic>? ?? <dynamic>[];
        return list
            .map(
              (dynamic item) => MessageModel.fromJson(item as Map<String, dynamic>),
            )
            .toList();
      },
    );
  }

  Future<Result<void>> deleteConversation(String conversationId) async {
    return _client.delete('$_path/$conversationId');
  }
}
