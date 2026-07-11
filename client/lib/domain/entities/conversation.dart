/// A conversation record.
class Conversation {
  const Conversation({
    required this.id,
    this.title = '',
    this.resourceIds = const <String>[],
    this.modelConfig,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String title;
  final List<String> resourceIds;
  final Map<String, dynamic>? modelConfig;
  final DateTime createdAt;
  final DateTime updatedAt;

  Conversation copyWith({
    String? id,
    String? title,
    List<String>? resourceIds,
    Map<String, dynamic>? modelConfig,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Conversation(
      id: id ?? this.id,
      title: title ?? this.title,
      resourceIds: resourceIds ?? this.resourceIds,
      modelConfig: modelConfig ?? this.modelConfig,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
