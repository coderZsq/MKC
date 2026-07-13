import '../../../shared/result.dart';
import '../../models/resource_model.dart';
import 'api_client.dart';

/// Remote resource API endpoints.
class ResourceApi {
  ResourceApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  static const String _path = '/resources';

  Future<Result<List<ResourceModel>>> list({
    required int page,
    required int limit,
    String? tag,
  }) async {
    return _client.get<List<ResourceModel>>(
      _path,
      queryParameters: <String, dynamic>{
        'page': page,
        'limit': limit,
        if (tag != null && tag.isNotEmpty) 'tag': tag,
      },
      parser: (dynamic data) {
        final items = switch (data) {
          {'items': final List<dynamic> values} => values,
          final List<dynamic> values => values,
          _ => <dynamic>[],
        };
        return items
            .map((dynamic item) =>
                ResourceModel.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }
}
