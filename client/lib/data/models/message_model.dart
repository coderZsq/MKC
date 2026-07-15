import '../../domain/entities/content_type.dart';
import '../../domain/entities/message.dart';

/// Data transfer object for a chat message returned by the API.
class MessageModel {
  const MessageModel({
    required this.messageId,
    required this.conversationId,
    required this.role,
    required this.content,
    required this.reasoning,
    required this.citations,
    required this.createdAt,
  });

  final String messageId;
  final String conversationId;
  final String role;
  final String content;
  final String reasoning;
  final List<CitationModel> citations;
  final DateTime createdAt;

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    return MessageModel(
      messageId: json['id'] as String? ?? (json['message_id'] as String? ?? ''),
      conversationId: json['conversation_id'] as String? ?? '',
      role: json['role'] as String? ?? 'user',
      content: json['content'] as String? ?? '',
      reasoning: json['reasoning'] as String? ?? '',
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
      reasoning: reasoning,
      citations: citations.map((c) => c.toDomain()).toList(),
      createdAt: createdAt,
    );
  }

  static List<CitationModel> _parseCitations(List<dynamic>? raw) {
    if (raw == null) return const <CitationModel>[];
    return raw
        .map((dynamic item) =>
            CitationModel.fromJson(item as Map<String, dynamic>))
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
    this.index,
    this.originalIndex,
    this.chunkId,
    this.page,
    this.timestamp,
    this.timestampEnd,
    this.snippet,
    required this.score,
    this.contentType,
  });

  final String resourceId;
  final String resourceName;
  final int? index;
  final int? originalIndex;
  final String? chunkId;
  final String? page;
  final Duration? timestamp;
  final Duration? timestampEnd;
  final String? snippet;
  final double score;
  final String? contentType;

  factory CitationModel.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] as Map<String, dynamic>? ?? const {};
    return CitationModel(
      resourceId: json['resource_id'] as String? ?? '',
      resourceName: json['resource_name'] as String? ?? '',
      index: _parseInt(json['index'] ?? metadata['index']),
      originalIndex:
          _parseInt(json['original_index'] ?? metadata['original_index']),
      chunkId: json['chunk_id'] as String? ?? metadata['chunk_id'] as String?,
      page: (json['page'] ?? metadata['page'])?.toString(),
      timestamp: _parseTimestamp(
        json['timestamp_start'] ??
            json['timestamp'] ??
            metadata['timestamp_start'] ??
            metadata['timestamp'],
      ),
      timestampEnd: _parseTimestamp(
        json['timestamp_end'] ?? metadata['timestamp_end'],
      ),
      snippet: json['snippet'] as String? ?? metadata['snippet'] as String?,
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      contentType: json['resource_type'] as String? ??
          json['content_type'] as String? ??
          metadata['content_type'] as String?,
    );
  }

  Citation toDomain() {
    return Citation(
      resourceId: resourceId,
      resourceName: resourceName,
      index: index,
      originalIndex: originalIndex,
      chunkId: chunkId,
      page: page,
      timestamp: timestamp,
      timestampEnd: timestampEnd,
      snippet: snippet,
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

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
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
