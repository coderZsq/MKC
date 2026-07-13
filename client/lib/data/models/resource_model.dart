import '../../domain/entities/resource.dart';

/// Data transfer object for resources returned by the API.
class ResourceModel {
  const ResourceModel({
    required this.resourceId,
    required this.name,
    required this.type,
    required this.status,
    required this.updatedAt,
    this.taskId,
    this.summary,
    this.summaryTruncated = false,
    this.tags = const <String>[],
  });

  final String resourceId;
  final String? taskId;
  final String name;
  final String type;
  final String status;
  final String? summary;
  final bool summaryTruncated;
  final List<String> tags;
  final DateTime updatedAt;

  factory ResourceModel.fromJson(Map<String, dynamic> json) {
    final rawTags = json['tags'];
    return ResourceModel(
      resourceId: json['resource_id'] as String? ?? json['id'] as String? ?? '',
      taskId: json['task_id'] as String?,
      name: json['name'] as String? ?? '',
      type: json['type'] as String? ?? '',
      status: json['status'] as String? ?? '',
      summary: json.containsKey('summary') ? json['summary'] as String? : null,
      summaryTruncated: json['summary_truncated'] as bool? ?? false,
      tags: rawTags is List
          ? rawTags
              .whereType<String>()
              .map((tag) => tag.trim())
              .where((tag) => tag.isNotEmpty)
              .toList(growable: false)
          : const <String>[],
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
    );
  }

  Resource toDomain() {
    return Resource(
      id: resourceId,
      taskId: taskId,
      name: name,
      type: type,
      status: status,
      summary: summary,
      summaryTruncated: summaryTruncated,
      tags: List<String>.unmodifiable(tags),
      updatedAt: updatedAt,
    );
  }
}
