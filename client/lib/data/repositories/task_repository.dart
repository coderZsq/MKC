import '../../data/datasources/remote/task_api.dart';
import '../../domain/entities/task.dart';
import '../../domain/repositories/task_repository.dart';
import '../../shared/result.dart';

/// Coordinates task API calls and maps data models to domain entities.
class TaskRepositoryImpl implements TaskRepository {
  TaskRepositoryImpl({required TaskApi api}) : _api = api;

  final TaskApi _api;

  @override
  Future<Result<List<Task>>> getTasks({required int page, required int limit}) async {
    final result = await _api.list(page: page, limit: limit);
    return result.when(
      success: (models) => Result.success(models.map((m) => m.toDomain()).toList()),
      failure: (error) => Result<List<Task>>.failure(error),
    );
  }

  @override
  Future<Result<Task>> getTask(String taskId) async {
    final result = await _api.get(taskId);
    return result.when(
      success: (model) => Result.success(model.toDomain()),
      failure: (error) => Result<Task>.failure(error),
    );
  }
}
