import 'package:mkc_client/domain/entities/resource.dart';
import 'package:mkc_client/domain/repositories/resource_repository.dart';
import 'package:mkc_client/shared/result.dart';

Resource createResource({
  String id = 'res-1',
  String name = 'report.pdf',
  String type = 'pdf_parse',
  String status = 'completed',
  String? summary = '这是一段摘要',
  bool summaryTruncated = false,
  List<String> tags = const <String>['机器学习'],
  DateTime? updatedAt,
}) {
  return Resource(
    id: id,
    name: name,
    type: type,
    status: status,
    summary: summary,
    summaryTruncated: summaryTruncated,
    tags: tags,
    updatedAt: updatedAt ?? DateTime(2026, 7, 12, 10, 30),
  );
}

class FakeResourceRepository implements ResourceRepository {
  Result<List<Resource>>? nextResourcesResult;
  final Map<String, Result<List<Resource>>> tagResults = {};
  int listCalls = 0;
  int lastPage = 0;
  int lastLimit = 0;
  String? lastTag;

  @override
  Future<Result<List<Resource>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  }) async {
    listCalls++;
    lastPage = page;
    lastLimit = limit;
    lastTag = tag;
    if (tag != null && tagResults.containsKey(tag)) {
      return tagResults[tag]!;
    }
    return nextResourcesResult ?? const Result.success([]);
  }
}
