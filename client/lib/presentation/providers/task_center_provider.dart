import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/datasources/remote/task_api.dart';
import '../../data/repositories/task_repository.dart';
import '../../domain/entities/task.dart';
import '../../domain/repositories/task_repository.dart';
import '../../shared/errors/app_exception.dart';
import 'app_provider.dart';

const int _defaultPageSize = 20;

/// UI state for the task center.
class TaskCenterState {
  const TaskCenterState({
    this.tasks = const <Task>[],
    this.currentPage = 1,
    this.hasMore = true,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
  });

  final List<Task> tasks;
  final int currentPage;
  final bool hasMore;
  final bool isLoading;
  final bool isLoadingMore;
  final AppException? error;

  TaskCenterState copyWith({
    List<Task>? tasks,
    int? currentPage,
    bool? hasMore,
    bool? isLoading,
    bool? isLoadingMore,
    AppException? error,
  }) {
    return TaskCenterState(
      tasks: tasks ?? this.tasks,
      currentPage: currentPage ?? this.currentPage,
      hasMore: hasMore ?? this.hasMore,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      error: error,
    );
  }
}

/// Manages task list state including pagination, refresh and errors.
class TaskCenterNotifier extends StateNotifier<TaskCenterState> {
  TaskCenterNotifier({required TaskRepository repository})
      : _repository = repository,
        super(const TaskCenterState());

  final TaskRepository _repository;

  Future<void> loadInitial() async {
    state = state.copyWith(isLoading: true, error: null, currentPage: 1, hasMore: true);
    final result = await _repository.getTasks(page: 1, limit: _defaultPageSize);
    state = result.when(
      success: (tasks) => state.copyWith(
        isLoading: false,
        tasks: tasks,
        hasMore: tasks.length == _defaultPageSize,
        currentPage: 1,
      ),
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;

    final nextPage = state.currentPage + 1;
    state = state.copyWith(isLoadingMore: true, error: null);
    final result = await _repository.getTasks(page: nextPage, limit: _defaultPageSize);
    state = result.when(
      success: (tasks) => state.copyWith(
        isLoadingMore: false,
        tasks: <Task>[...state.tasks, ...tasks],
        hasMore: tasks.length == _defaultPageSize,
        currentPage: nextPage,
      ),
      failure: (error) => state.copyWith(isLoadingMore: false, error: error),
    );
  }

  Future<void> refresh() async {
    await loadInitial();
  }
}

final taskApiProvider = Provider<TaskApi>((ref) {
  return TaskApi(client: ref.watch(apiClientProvider));
});

final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  return TaskRepositoryImpl(api: ref.watch(taskApiProvider));
});

final taskCenterNotifierProvider =
    StateNotifierProvider.autoDispose<TaskCenterNotifier, TaskCenterState>((ref) {
  return TaskCenterNotifier(repository: ref.watch(taskRepositoryProvider));
});
