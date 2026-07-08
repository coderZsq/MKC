/// Domain event pushed from the gateway for a task.
class TaskEvent {
  const TaskEvent({
    required this.taskId,
    required this.eventType,
    required this.status,
    required this.progress,
    this.message,
    required this.timestamp,
  });

  final String taskId;
  final String eventType;
  final String status;
  final int progress;
  final String? message;
  final DateTime timestamp;

  factory TaskEvent.fromJson(
    Map<String, dynamic> json, {
    String eventType = 'status',
  }) {
    return TaskEvent(
      taskId: json['task_id'] as String? ?? '',
      eventType: eventType,
      status: json['status'] as String? ?? '',
      progress: json['progress'] as int? ?? 0,
      message: json['message'] as String?,
      timestamp: _parseTimestamp(json['timestamp']),
    );
  }

  static DateTime _parseTimestamp(dynamic value) {
    if (value is String) {
      return DateTime.tryParse(value)?.toLocal() ?? DateTime.now();
    }
    return DateTime.now();
  }
}
