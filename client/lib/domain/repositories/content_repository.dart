import '../../shared/result.dart';
import '../entities/content.dart';
import '../entities/content_type.dart';

/// Abstract repository for loading task result content.
abstract class ContentRepository {
  /// Fetches and parses task result content for the given task and content type.
  Future<Result<Content>> getContent(
    String taskId,
    ContentType contentType,
  );
}
