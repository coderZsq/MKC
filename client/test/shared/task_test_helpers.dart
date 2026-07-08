import 'package:mkc_client/domain/entities/task.dart';
import 'package:mkc_client/domain/repositories/task_repository.dart';
import 'package:mkc_client/shared/result.dart';

Task createTask({
  String id = 'task-1',
  String resourceId = 'res-1',
  String resourceName = 'test.pdf',
  TaskType type = TaskType.pdfParse,
  TaskStatus status = TaskStatus.pending,
  int progress = 0,
  String? errorMessage,
  DateTime? updatedAt,
}) {
  return Task(
    id: id,
    resourceId: resourceId,
    resourceName: resourceName,
    type: type,
    status: status,
    progress: progress,
    errorMessage: errorMessage,
    updatedAt: updatedAt ?? DateTime(2024, 1, 1, 12, 0),
  );
}

class FakeTaskRepository implements TaskRepository {
  Result<List<Task>>? nextTasksResult;
  Result<Task>? nextTaskResult;
  int listCalls = 0;
  int getCalls = 0;
  int lastPage = 0;
  int lastLimit = 0;

  @override
  Future<Result<List<Task>>> getTasks({required int page, required int limit}) async {
    listCalls++;
    lastPage = page;
    lastLimit = limit;
    return nextTasksResult ?? const Result.success([]);
  }

  @override
  Future<Result<Task>> getTask(String taskId) async {
    getCalls++;
    return nextTaskResult ?? Result.success(createTask(id: taskId));
  }
}
