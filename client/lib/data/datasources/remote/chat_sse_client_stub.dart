import '../../../domain/entities/chat_event.dart';
import '../../../domain/repositories/token_provider.dart';
import 'chat_sse_client.dart';

/// Stub implementation used when no platform-specific SSE client is available.
class ChatSseClientImpl implements ChatSseClient {
  ChatSseClientImpl({
    required String baseUrl,
    required TokenProvider tokenProvider,
  });

  @override
  Stream<ChatEvent> ask(String conversationId, String question) {
    throw UnsupportedError(
      'ChatSseClient is not supported on this platform.',
    );
  }
}
