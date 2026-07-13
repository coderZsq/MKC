import '../../domain/entities/resource.dart';
import '../../domain/repositories/resource_repository.dart';
import '../../shared/errors/app_exception.dart';
import '../../shared/result.dart';
import '../datasources/remote/resource_api.dart';

/// Coordinates resource API calls and maps data models to domain entities.
class ResourceRepositoryImpl implements ResourceRepository {
  ResourceRepositoryImpl({required ResourceApi api}) : _api = api;

  final ResourceApi _api;

  static const int maxTagLength = 32;

  @override
  Future<Result<List<Resource>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  }) async {
    final normalizedTag = tag?.trim();
    if (normalizedTag != null && normalizedTag.isEmpty) {
      return const Result.failure(ValidationException({'tag': '标签不能为空'}));
    }
    if (normalizedTag != null && normalizedTag.runes.length > maxTagLength) {
      return const Result.failure(ValidationException({'tag': '标签长度超限'}));
    }

    final result =
        await _api.list(page: page, limit: limit, tag: normalizedTag);
    return result.when(
      success: (models) => Result.success(
          models.map((model) => model.toDomain()).toList(growable: false)),
      failure: (error) => Result<List<Resource>>.failure(error),
    );
  }
}
