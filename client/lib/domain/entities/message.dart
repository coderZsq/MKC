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
    this.page,
    this.timestamp,
    required this.score,
    this.contentType = ContentType.pdf,
  });

  final String resourceId;
  final String resourceName;
  final String? page;
  final Duration? timestamp;
  final double score;
  final ContentType contentType;

  Citation copyWith({
    String? resourceId,
    String? resourceName,
    String? page,
    Duration? timestamp,
    double? score,
    ContentType? contentType,
  }) {
    return Citation(
      resourceId: resourceId ?? this.resourceId,
      resourceName: resourceName ?? this.resourceName,
      page: page ?? this.page,
      timestamp: timestamp ?? this.timestamp,
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
    this.citations = const <Citation>[],
    required this.createdAt,
    this.isStreaming = false,
  });

  final String id;
  final String conversationId;
  final MessageRole role;
  final String content;
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
    List<Citation> citations = const <Citation>[],
    DateTime? createdAt,
    bool isStreaming = false,
  }) {
    return Message(
      id: id ?? '',
      conversationId: conversationId,
      role: MessageRole.assistant,
      content: content,
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
    List<Citation>? citations,
    DateTime? createdAt,
    bool? isStreaming,
  }) {
    return Message(
      id: id ?? this.id,
      conversationId: conversationId ?? this.conversationId,
      role: role ?? this.role,
      content: content ?? this.content,
      citations: citations ?? this.citations,
      createdAt: createdAt ?? this.createdAt,
      isStreaming: isStreaming ?? this.isStreaming,
    );
  }
}
