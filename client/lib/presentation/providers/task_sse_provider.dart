import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/env.dart';
import '../../data/datasources/remote/task_sse_client.dart';
import '../../domain/entities/task.dart';
import '../../domain/entities/task_event.dart';
import 'app_provider.dart';

/// Platform-aware SSE client for task progress events.
final taskSseClientProvider = Provider<TaskSseClient>((ref) {
  return TaskSseClient(
    baseUrl: Env.baseUrl,
    tokenProvider: ref.watch(tokenProvider),
  );
});

/// Live task event stream for a single task.
///
/// Only subscribes when the task is in a non-terminal state. The stream is
/// cancelled automatically when the provider is disposed.
final taskEventStreamProvider = StreamProvider.autoDispose
    .family<TaskEvent?, String>((ref, taskId) {
  final client = ref.watch(taskSseClientProvider);
  return client
      .subscribe(taskId)
      .where((event) => event.taskId == taskId)
      .handleError((Object _) {
    // Errors are already handled by the client (reconnect / polling fallback).
  });
});

/// Returns the latest [Task] for a list item, applying any live SSE updates.
Task taskWithEvent(Task task, AsyncValue<TaskEvent?> eventAsync) {
  return eventAsync.when(
    data: (event) {
      if (event == null) return task;
      return task.copyWith(
        status: parseTaskStatus(event.status),
        progress: event.progress.clamp(0, 100),
        errorMessage: event.message,
      );
    },
    loading: () => task,
    error: (_, __) => task,
  );
}
