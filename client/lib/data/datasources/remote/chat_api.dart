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

  Future<Result<ConversationModel>> createConversation({
    String? title,
    List<String>? resourceIds,
  }) async {
    final body = <String, dynamic>{};
    if (title != null && title.isNotEmpty) {
      body['title'] = title;
    }
    if (resourceIds != null && resourceIds.isNotEmpty) {
      body['resource_ids'] = resourceIds;
    }
    return _client.post<ConversationModel>(
      _path,
      data: body.isEmpty ? null : body,
      parser: (dynamic data) => ConversationModel.fromJson(data as Map<String, dynamic>),
    );
  }

  Future<Result<List<MessageModel>>> loadMessages(
    String conversationId, {
    int? page,
    int? limit,
  }) async {
    final queryParameters = <String, dynamic>{};
    if (page != null) queryParameters['page'] = page;
    if (limit != null) queryParameters['limit'] = limit;
    return _client.get<List<MessageModel>>(
      '$_path/$conversationId/messages',
      queryParameters: queryParameters.isEmpty ? null : queryParameters,
      parser: (dynamic data) {
        final envelope = data as Map<String, dynamic>? ?? const <String, dynamic>{};
        final list = envelope['items'] as List<dynamic>? ?? <dynamic>[];
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
