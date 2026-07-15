import 'content_type.dart';

/// Role of a message sender in a chat conversation.
enum MessageRole {
  user,
  assistant;

  static MessageRole fromString(String value) {
    return switch (value) {
      'assistant' => MessageRole.assistant,
      _ => MessageRole.user,
    };
  }
}

/// A single citation attached to an assistant message.
class Citation {
  const Citation({
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
    this.contentType = ContentType.pdf,
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
  final ContentType contentType;

  Citation copyWith({
    String? resourceId,
    String? resourceName,
    int? index,
    int? originalIndex,
    String? chunkId,
    String? page,
    Duration? timestamp,
    Duration? timestampEnd,
    String? snippet,
    double? score,
    ContentType? contentType,
  }) {
    return Citation(
      resourceId: resourceId ?? this.resourceId,
      resourceName: resourceName ?? this.resourceName,
      index: index ?? this.index,
      originalIndex: originalIndex ?? this.originalIndex,
      chunkId: chunkId ?? this.chunkId,
      page: page ?? this.page,
      timestamp: timestamp ?? this.timestamp,
      timestampEnd: timestampEnd ?? this.timestampEnd,
      snippet: snippet ?? this.snippet,
      score: score ?? this.score,
      contentType: contentType ?? this.contentType,
    );
  }
}

/// A single message in a conversation.
class Message {
  const Message({
    required this.id,
    required this.conversationId,
    required this.role,
    this.content = '',
    this.reasoning = '',
    this.citations = const <Citation>[],
    required this.createdAt,
    this.isStreaming = false,
  });

  final String id;
  final String conversationId;
  final MessageRole role;
  final String content;
  final String reasoning;
  final List<Citation> citations;
  final DateTime createdAt;
  final bool isStreaming;

  factory Message.user({
    String? id,
    required String conversationId,
    required String content,
    DateTime? createdAt,
  }) {
    return Message(
      id: id ?? '',
      conversationId: conversationId,
      role: MessageRole.user,
      content: content,
      createdAt: createdAt ?? DateTime.now(),
    );
  }

  factory Message.assistant({
    String? id,
    required String conversationId,
    String content = '',
    String reasoning = '',
    List<Citation> citations = const <Citation>[],
    DateTime? createdAt,
    bool isStreaming = false,
  }) {
    return Message(
      id: id ?? '',
      conversationId: conversationId,
      role: MessageRole.assistant,
      content: content,
      reasoning: reasoning,
      citations: citations,
      createdAt: createdAt ?? DateTime.now(),
      isStreaming: isStreaming,
    );
  }

  Message copyWith({
    String? id,
    String? conversationId,
    MessageRole? role,
    String? content,
    String? reasoning,
    List<Citation>? citations,
    DateTime? createdAt,
    bool? isStreaming,
  }) {
    return Message(
      id: id ?? this.id,
      conversationId: conversationId ?? this.conversationId,
      role: role ?? this.role,
      content: content ?? this.content,
      reasoning: reasoning ?? this.reasoning,
      citations: citations ?? this.citations,
      createdAt: createdAt ?? this.createdAt,
      isStreaming: isStreaming ?? this.isStreaming,
    );
  }

  Message withCitationMarkersSynced() {
    if (citations.isEmpty) return this;
    final markerMap = <int, int>{};
    for (final citation in citations) {
      final original = citation.originalIndex;
      final current = citation.index;
      if (original == null || current == null || original == current) {
        continue;
      }
      markerMap[original] = current;
    }
    if (markerMap.isEmpty) return this;
    return copyWith(
      content: _syncCitationMarkers(content, markerMap),
      reasoning: _syncCitationMarkers(reasoning, markerMap),
    );
  }
}

final RegExp _citationMarkerPattern = RegExp(r'\[\^(\d+)\]');

String _syncCitationMarkers(String text, Map<int, int> markerMap) {
  if (text.isEmpty) return text;
  return text.replaceAllMapped(_citationMarkerPattern, (match) {
    final original = int.tryParse(match.group(1) ?? '');
    final current = original == null ? null : markerMap[original];
    if (current == null) return match.group(0)!;
    return '[^$current]';
  });
}
