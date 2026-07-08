import '../../shared/result.dart';
import '../entities/task.dart';

/// Abstract repository for task operations.
abstract class TaskRepository {
  /// Fetches a paginated list of tasks for the current user.
  Future<Result<List<Task>>> getTasks({required int page, required int limit});

  /// Fetches a single task by id.
  Future<Result<Task>> getTask(String taskId);
}
