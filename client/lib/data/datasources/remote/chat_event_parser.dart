import 'dart:convert';

import '../../../domain/entities/chat_event.dart';
import '../../../domain/entities/message.dart';

/// Shared SSE event parser for both native and web SSE clients.
class ChatEventParser {
  const ChatEventParser._();

  /// Parses a decoded SSE event string into a [ChatEvent].
  static ChatEvent? parseEvent(String event) {
    String eventType = 'message';
    final dataBuffer = StringBuffer();
    final lines = event.split('\n');
    for (final line in lines) {
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        if (dataBuffer.isNotEmpty) {
          dataBuffer.write('\n');
        }
        dataBuffer.write(line.substring(5).trim());
      }
    }
    if (dataBuffer.isEmpty) return null;
    try {
      final json = jsonDecode(dataBuffer.toString()) as Map<String, dynamic>;
      return _buildEvent(json, eventType);
    } catch (_) {
      return null;
    }
  }

  /// Parses an already-split event type and data payload into a [ChatEvent].
  static ChatEvent? parseEventData(String eventType, String data) {
    if (data.isEmpty) return null;
    try {
      final json = jsonDecode(data) as Map<String, dynamic>;
      return _buildEvent(json, eventType);
    } catch (_) {
      return null;
    }
  }

  static ChatEvent _buildEvent(Map<String, dynamic> json, String eventType) {
    final metadata = json['metadata'] as Map<String, dynamic>? ?? const {};
    return ChatEvent(
      type: eventType,
      messageId: json['message_id'] as String? ?? '',
      conversationId: json['conversation_id'] as String?,
      delta: json['delta'] as String?,
      citation: eventType == 'citation' ? _parseCitation(json, metadata) : null,
      finishReason: json['finish_reason'] as String?,
      errorCode: json['error_code'] as String?,
      errorMessage: json['message'] as String?,
    );
  }

  static CitationData? _parseCitation(
    Map<String, dynamic> json,
    Map<String, dynamic> metadata,
  ) {
    final resourceId = json['resource_id'] as String?;
    if (resourceId == null || resourceId.isEmpty) return null;
    return CitationData(
      resourceId: resourceId,
      resourceName: json['resource_name'] as String? ?? '',
      page: metadata['page']?.toString(),
      timestamp: _parseDuration(metadata['timestamp']),
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      contentType: metadata['content_type'] as String?,
    );
  }

  /// Parses an assistant message from the fallback polling API.
  static Message parseAssistantMessage(Map<String, dynamic> raw) {
    return Message.assistant(
      id: raw['message_id'] as String? ?? '',
      conversationId: raw['conversation_id'] as String? ?? '',
      content: raw['content'] as String? ?? '',
      createdAt: _parseTimestamp(raw['created_at']),
      isStreaming: raw['is_streaming'] as bool? ?? false,
    );
  }

  static Duration? _parseDuration(dynamic value) {
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
