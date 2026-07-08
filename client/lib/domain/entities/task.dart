import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Domain entity representing an AI processing task.
class Task {
  const Task({
    required this.id,
    required this.resourceId,
    required this.resourceName,
    required this.type,
    required this.status,
    required this.progress,
    this.errorMessage,
    required this.updatedAt,
  });

  final String id;
  final String resourceId;
  final String resourceName;
  final TaskType type;
  final TaskStatus status;
  final int progress;
  final String? errorMessage;
  final DateTime updatedAt;
}

/// Task processing status.
enum TaskStatus {
  pending,
  running,
  completed,
  failed;

  String get label {
    return switch (this) {
      TaskStatus.pending => '等待中',
      TaskStatus.running => '处理中',
      TaskStatus.completed => '已完成',
      TaskStatus.failed => '失败',
    };
  }

  Color get color {
    return switch (this) {
      TaskStatus.pending => Colors.grey,
      TaskStatus.running => Colors.blue,
      TaskStatus.completed => Colors.green,
      TaskStatus.failed => Colors.red,
    };
  }
}

/// Parses a backend status string into [TaskStatus].
TaskStatus parseTaskStatus(String raw) {
  return switch (raw) {
    'running' => TaskStatus.running,
    'completed' => TaskStatus.completed,
    'failed' => TaskStatus.failed,
    _ => TaskStatus.pending,
  };
}

/// Task type describing the kind of AI processing requested.
enum TaskType {
  mediaParse,
  pdfParse,
  documentParse;

  String get label {
    return switch (this) {
      TaskType.mediaParse => '音视频解析',
      TaskType.pdfParse => 'PDF 解析',
      TaskType.documentParse => '文档解析',
    };
  }
}

/// Parses a backend type string into [TaskType].
TaskType parseTaskType(String raw) {
  return switch (raw) {
    'media_parse' => TaskType.mediaParse,
    'pdf_parse' => TaskType.pdfParse,
    'document_parse' => TaskType.documentParse,
    _ => TaskType.documentParse,
  };
}

/// Formats a task update timestamp for list display.
String formatTaskUpdatedAt(DateTime updatedAt) {
  return DateFormat('yyyy-MM-dd HH:mm').format(updatedAt.toLocal());
}
