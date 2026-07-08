import '../../domain/entities/task.dart';

/// Data transfer object for a task returned by the API.
class TaskModel {
  const TaskModel({
    required this.taskId,
    required this.resourceId,
    required this.resourceName,
    required this.type,
    required this.status,
    required this.progress,
    this.errorMessage,
    required this.updatedAt,
  });

  final String taskId;
  final String resourceId;
  final String resourceName;
  final String type;
  final String status;
  final int progress;
  final String? errorMessage;
  final DateTime updatedAt;

  factory TaskModel.fromJson(Map<String, dynamic> json) {
    return TaskModel(
      taskId: json['task_id'] as String? ?? '',
      resourceId: json['resource_id'] as String? ?? '',
      resourceName: json['resource_name'] as String? ?? '',
      type: json['type'] as String? ?? 'document_parse',
      status: json['status'] as String? ?? 'pending',
      progress: json['progress'] as int? ?? 0,
      errorMessage: json['error_message'] as String?,
      updatedAt: _parseUpdatedAt(json['updated_at']),
    );
  }

  static DateTime _parseUpdatedAt(dynamic value) {
    if (value is int) {
      return DateTime.fromMillisecondsSinceEpoch(value * 1000);
    }
    if (value is String) {
      return DateTime.tryParse(value) ?? DateTime.now();
    }
    return DateTime.now();
  }

  Task toDomain() {
    return Task(
      id: taskId,
      resourceId: resourceId,
      resourceName: resourceName,
      type: parseTaskType(type),
      status: parseTaskStatus(status),
      progress: progress,
      errorMessage: errorMessage,
      updatedAt: updatedAt,
    );
  }
}
