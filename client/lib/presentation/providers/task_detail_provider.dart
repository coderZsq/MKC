import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/task.dart';
import '../../domain/entities/task_event.dart';
import '../../domain/repositories/task_repository.dart';
import '../../shared/errors/app_exception.dart';
import 'task_center_provider.dart';

/// UI state for the task detail page.
class TaskDetailState {
  const TaskDetailState({
    this.task,
    this.isLoading = false,
    this.error,
  });

  final Task? task;
  final bool isLoading;
  final AppException? error;

  TaskDetailState copyWith({
    Task? task,
    bool? isLoading,
    AppException? error,
  }) {
    return TaskDetailState(
      task: task ?? this.task,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Manages loading a single task.
class TaskDetailNotifier extends StateNotifier<TaskDetailState> {
  TaskDetailNotifier({
    required TaskRepository repository,
    required String taskId,
  })  : _repository = repository,
        _taskId = taskId,
        super(const TaskDetailState());

  final TaskRepository _repository;
  final String _taskId;

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repository.getTask(_taskId);
    state = result.when(
      success: (task) => state.copyWith(isLoading: false, task: task),
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  void applyTaskEvent(TaskEvent event) {
    final current = state.task;
    if (current == null || current.id != event.taskId) return;

    state = state.copyWith(
      task: current.copyWith(
        status: parseTaskStatus(event.status),
        progress: event.progress.clamp(0, 100),
        errorMessage: event.message,
        updatedAt: event.timestamp,
      ),
    );
  }
}

final taskDetailNotifierProvider = StateNotifierProvider.autoDispose
    .family<TaskDetailNotifier, TaskDetailState, String>((ref, taskId) {
  return TaskDetailNotifier(
    repository: ref.watch(taskRepositoryProvider),
    taskId: taskId,
  );
});
