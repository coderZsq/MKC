import 'task_sse_client_default.dart'
    if (dart.library.html) 'task_sse_client_web.dart';

import '../../../domain/entities/task_event.dart';
import '../../../domain/repositories/token_provider.dart';

/// Platform-aware SSE client for task progress events.
abstract class TaskSseClient {
  /// Creates the correct implementation for the current platform.
  ///
  /// On the Web this uses `EventSource`; on mobile/desktop it uses
  /// Dio's response stream parser.
  factory TaskSseClient({
    required String baseUrl,
    required TokenProvider tokenProvider,
  }) = TaskSseClientImpl;

  /// Subscribes to server-sent events for [taskId].
  ///
  /// The returned stream automatically reconnects up to 5 times on failure
  /// and falls back to a 5-second polling stream if SSE cannot be established.
  Stream<TaskEvent> subscribe(String taskId);
}
