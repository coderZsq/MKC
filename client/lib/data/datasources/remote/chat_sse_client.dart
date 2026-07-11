import 'chat_sse_client_stub.dart'
    if (dart.library.io) 'chat_sse_client_default.dart'
    if (dart.library.js_interop) 'chat_sse_client_web.dart';

import '../../../domain/entities/chat_event.dart';
import '../../../domain/repositories/token_provider.dart';

/// Platform-aware SSE client for chat answer events.
abstract class ChatSseClient {
  /// Creates the correct implementation for the current platform.
  factory ChatSseClient({
    required String baseUrl,
    required TokenProvider tokenProvider,
  }) = ChatSseClientImpl;

  /// Asks a question in [conversationId] and returns the SSE answer stream.
  Stream<ChatEvent> ask(String conversationId, String question);
}
