import '../../domain/entities/task.dart';

/// Data transfer object for the task result summary API.
class TaskResultModel {
  const TaskResultModel({
    required this.taskId,
    required this.status,
    required this.files,
    this.metadata = const {},
  });

  final String taskId;
  final TaskStatus status;
  final ResultFiles files;
  final Map<String, dynamic> metadata;

  factory TaskResultModel.fromJson(Map<String, dynamic> json) {
    return TaskResultModel(
      taskId: json['task_id'] as String? ?? '',
      status: parseTaskStatus(json['status'] as String? ?? 'pending'),
      files: ResultFiles.fromJson(
        (json['files'] as Map<String, dynamic>?) ?? const {},
      ),
      metadata: (json['metadata'] as Map<String, dynamic>?) ?? const {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'task_id': taskId,
      'status': status.name,
      'files': files.toJson(),
      'metadata': metadata,
    };
  }

  TaskResultModel copyWith({
    String? taskId,
    TaskStatus? status,
    ResultFiles? files,
    Map<String, dynamic>? metadata,
  }) {
    return TaskResultModel(
      taskId: taskId ?? this.taskId,
      status: status ?? this.status,
      files: files ?? this.files,
      metadata: metadata ?? this.metadata,
    );
  }
}

/// Signed URLs for result files returned by the result API.
class ResultFiles {
  const ResultFiles({
    this.transcriptUrl,
    this.subtitleUrl,
    this.parsedUrl,
  });

  final String? transcriptUrl;
  final String? subtitleUrl;
  final String? parsedUrl;

  factory ResultFiles.fromJson(Map<String, dynamic> json) {
    return ResultFiles(
      transcriptUrl: json['transcript_url'] as String?,
      subtitleUrl: json['subtitle_url'] as String?,
      parsedUrl: json['parsed_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'transcript_url': transcriptUrl,
      'subtitle_url': subtitleUrl,
      'parsed_url': parsedUrl,
    };
  }

  ResultFiles copyWith({
    String? transcriptUrl,
    String? subtitleUrl,
    String? parsedUrl,
  }) {
    return ResultFiles(
      transcriptUrl: transcriptUrl ?? this.transcriptUrl,
      subtitleUrl: subtitleUrl ?? this.subtitleUrl,
      parsedUrl: parsedUrl ?? this.parsedUrl,
    );
  }
}
