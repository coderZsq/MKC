import '../../domain/entities/conversation.dart';

/// Data transfer object for a conversation returned by the API.
class ConversationModel {
  const ConversationModel({
    required this.conversationId,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
  });

  final String conversationId;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ConversationModel.fromJson(Map<String, dynamic> json) {
    return ConversationModel(
      conversationId: json['conversation_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      createdAt: _parseTimestamp(json['created_at']),
      updatedAt: _parseTimestamp(json['updated_at']),
    );
  }

  Conversation toDomain() {
    return Conversation(
      id: conversationId,
      title: title,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
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
