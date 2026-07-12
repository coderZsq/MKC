/// Response returned by `POST /files/upload`.
class UploadResponseModel {
  const UploadResponseModel({
    required this.resourceId,
    required this.taskId,
    required this.name,
    required this.type,
    required this.status,
    required this.sizeBytes,
    this.mimeType,
    required this.createdAt,
    this.autoSummary = true,
  });

  factory UploadResponseModel.fromJson(Map<String, dynamic> json) {
    return UploadResponseModel(
      resourceId: json['resource_id'] as String,
      taskId: json['task_id'] as String,
      name: json['name'] as String,
      type: json['type'] as String,
      status: json['status'] as String,
      sizeBytes: json['size_bytes'] as int,
      mimeType: json['mime_type'] as String?,
      createdAt: json['created_at'] as int,
      autoSummary: json['auto_summary'] as bool? ?? true,
    );
  }

  final String resourceId;
  final String taskId;
  final String name;
  final String type;
  final String status;
  final int sizeBytes;
  final String? mimeType;
  final int createdAt;
  final bool autoSummary;

  Map<String, dynamic> toJson() => {
        'resource_id': resourceId,
        'task_id': taskId,
        'name': name,
        'type': type,
        'status': status,
        'size_bytes': sizeBytes,
        'mime_type': mimeType,
        'created_at': createdAt,
        'auto_summary': autoSummary,
      };
}
