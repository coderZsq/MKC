/// A single server-sent event delivered by the chat SSE endpoint.
class ChatEvent {
  const ChatEvent({
    required this.type,
    required this.messageId,
    this.conversationId,
    this.delta,
    this.citation,
    this.finishReason,
    this.errorCode,
    this.errorMessage,
  });

  final String type;
  final String messageId;
  final String? conversationId;
  final String? delta;
  final CitationData? citation;
  final String? finishReason;
  final String? errorCode;
  final String? errorMessage;

  bool get isTerminal => type == 'done' || type == 'error';
}

/// Raw citation data attached to a chat SSE event.
class CitationData {
  const CitationData({
    required this.resourceId,
    this.resourceName,
    this.page,
    this.timestamp,
    required this.score,
    this.contentType,
  });

  final String resourceId;
  final String? resourceName;
  final String? page;
  final Duration? timestamp;
  final double score;
  final String? contentType;
}
