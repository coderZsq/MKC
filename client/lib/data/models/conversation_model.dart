import '../../domain/entities/conversation.dart';

/// Data transfer object for a conversation returned by the API.
class ConversationModel {
  const ConversationModel({
    required this.conversationId,
    required this.title,
    this.resourceIds = const <String>[],
    this.modelConfig,
    required this.createdAt,
    required this.updatedAt,
  });

  final String conversationId;
  final String title;
  final List<String> resourceIds;
  final Map<String, dynamic>? modelConfig;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ConversationModel.fromJson(Map<String, dynamic> json) {
    return ConversationModel(
      conversationId: json['id'] as String? ??
          (json['conversation_id'] as String? ?? ''),
      title: json['title'] as String? ?? '',
      resourceIds: _parseStringList(json['resource_ids']),
      modelConfig: json['model_config'] as Map<String, dynamic>?,
      createdAt: _parseTimestamp(json['created_at']),
      updatedAt: _parseTimestamp(json['updated_at']),
    );
  }

  Conversation toDomain() {
    return Conversation(
      id: conversationId,
      title: title,
      resourceIds: resourceIds,
      modelConfig: modelConfig,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }

  static List<String> _parseStringList(dynamic value) {
    if (value is! List<dynamic>) return const <String>[];
    return value
        .map((dynamic item) => item?.toString() ?? '')
        .where((item) => item.isNotEmpty)
        .toList();
  }

  static DateTime _parseTimestamp(dynamic value) {
    if (value is int) {
      return DateTime.fromMillisecondsSinceEpoch(value * 1000);
    }
    if (value is String) {
      return DateTime.tryParse(value)?.toLocal() ?? DateTime.now();
    }
    return DateTime.now();
  }
}
