import '../../shared/result.dart';
import '../entities/resource.dart';

/// Repository contract for resource list data.
abstract class ResourceRepository {
  Future<Result<List<Resource>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  });
}
