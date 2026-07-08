import '../../models/auth_token_model.dart';
import '../../models/login_request_model.dart';
import '../../models/register_request_model.dart';
import 'api_client.dart';
import '../../../shared/result.dart';

/// Remote authentication API endpoints.
class AuthApi {
  AuthApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  Future<Result<AuthTokenModel>> login(LoginRequestModel req) async {
    return _client.post<AuthTokenModel>(
      '/auth/login',
      data: req.toJson(),
      parser: (dynamic data) =>
          AuthTokenModel.fromJson(data as Map<String, dynamic>),
    );
  }

  Future<Result<AuthTokenModel>> register(RegisterRequestModel req) async {
    return _client.post<AuthTokenModel>(
      '/auth/register',
      data: req.toJson(),
      parser: (dynamic data) =>
          AuthTokenModel.fromJson(data as Map<String, dynamic>),
    );
  }
}
