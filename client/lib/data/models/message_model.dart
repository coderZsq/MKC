import '../../domain/entities/content_type.dart';
import '../../domain/entities/message.dart';

/// Data transfer object for a chat message returned by the API.
class MessageModel {
  const MessageModel({
    required this.messageId,
    required this.conversationId,
    required this.role,
    required this.content,
    required this.citations,
    required this.createdAt,
  });

  final String messageId;
  final String conversationId;
  final String role;
  final String content;
  final List<CitationModel> citations;
  final DateTime createdAt;

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    return MessageModel(
      messageId: json['id'] as String? ?? (json['message_id'] as String? ?? ''),
      conversationId: json['conversation_id'] as String? ?? '',
      role: json['role'] as String? ?? 'user',
      content: json['content'] as String? ?? '',
      citations: _parseCitations(json['citations'] as List<dynamic>?),
      createdAt: _parseTimestamp(json['created_at']),
    );
  }

  Message toDomain() {
    return Message(
      id: messageId,
      conversationId: conversationId,
      role: MessageRole.fromString(role),
      content: content,
      citations: citations.map((c) => c.toDomain()).toList(),
      createdAt: createdAt,
    );
  }

  static List<CitationModel> _parseCitations(List<dynamic>? raw) {
    if (raw == null) return const <CitationModel>[];
    return raw
        .map((dynamic item) => CitationModel.fromJson(item as Map<String, dynamic>))
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

/// Data transfer object for a citation returned by the API.
class CitationModel {
  const CitationModel({
    required this.resourceId,
    required this.resourceName,
    this.page,
    this.timestamp,
    required this.score,
    this.contentType,
  });

  final String resourceId;
  final String resourceName;
  final String? page;
  final Duration? timestamp;
  final double score;
  final String? contentType;

  factory CitationModel.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] as Map<String, dynamic>? ?? const {};
    return CitationModel(
      resourceId: json['resource_id'] as String? ?? '',
      resourceName: json['resource_name'] as String? ?? '',
      page: metadata['page']?.toString(),
      timestamp: _parseTimestamp(metadata['timestamp']),
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      contentType: metadata['content_type'] as String?,
    );
  }

  Citation toDomain() {
    return Citation(
      resourceId: resourceId,
      resourceName: resourceName,
      page: page,
      timestamp: timestamp,
      score: score,
      contentType: _parseContentType(contentType),
    );
  }

  static ContentType _parseContentType(String? value) {
    return switch (value) {
      'audio' => ContentType.audio,
      _ => ContentType.pdf,
    };
  }

  static Duration? _parseTimestamp(dynamic value) {
    if (value == null) return null;
    if (value is int) return Duration(seconds: value);
    if (value is double) {
      return Duration(milliseconds: (value * 1000).round());
    }
    if (value is String) {
      final seconds = double.tryParse(value);
      if (seconds == null) return null;
      return Duration(milliseconds: (seconds * 1000).round());
    }
    return null;
  }
}
