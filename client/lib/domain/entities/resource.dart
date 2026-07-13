/// Domain entity for a user-owned resource in the resource list.
class Resource {
  const Resource({
    required this.id,
    required this.name,
    required this.type,
    required this.status,
    required this.updatedAt,
    this.taskId,
    this.summary,
    this.summaryTruncated = false,
    this.tags = const <String>[],
  });

  final String id;
  final String? taskId;
  final String name;
  final String type;
  final String status;
  final String? summary;
  final bool summaryTruncated;
  final List<String> tags;
  final DateTime updatedAt;
}
