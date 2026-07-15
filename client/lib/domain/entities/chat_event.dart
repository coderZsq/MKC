/// A single server-sent event delivered by the chat SSE endpoint.
class ChatEvent {
  const ChatEvent({
    required this.type,
    required this.messageId,
    this.conversationId,
    this.delta,
    this.reasoningDelta,
    this.citation,
    this.finishReason,
    this.errorCode,
    this.errorMessage,
  });

  final String type;
  final String messageId;
  final String? conversationId;
  final String? delta;
  final String? reasoningDelta;
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
    this.index,
    this.originalIndex,
    this.chunkId,
    this.resourceName,
    this.page,
    this.timestamp,
    this.timestampEnd,
    this.snippet,
    required this.score,
    this.contentType,
  });

  final String resourceId;
  final int? index;
  final int? originalIndex;
  final String? chunkId;
  final String? resourceName;
  final String? page;
  final Duration? timestamp;
  final Duration? timestampEnd;
  final String? snippet;
  final double score;
  final String? contentType;
}
