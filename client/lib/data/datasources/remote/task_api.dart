import '../../../shared/result.dart';
import 'api_client.dart';
import '../../models/task_model.dart';

/// Remote task API endpoints.
class TaskApi {
  TaskApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  static const String _path = '/tasks';

  Future<Result<List<TaskModel>>> list({required int page, required int limit}) async {
    return _client.get<List<TaskModel>>(
      _path,
      queryParameters: <String, dynamic>{'page': page, 'limit': limit},
      parser: (dynamic data) {
        final list = data as List<dynamic>? ?? <dynamic>[];
        return list
            .map((dynamic item) => TaskModel.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }

  Future<Result<TaskModel>> get(String taskId) async {
    return _client.get<TaskModel>(
      '$_path/$taskId',
      parser: (dynamic data) => TaskModel.fromJson(data as Map<String, dynamic>),
    );
  }
}
