import '../models/auth_token_model.dart';
import '../models/login_request_model.dart';
import '../models/register_request_model.dart';
import '../datasources/remote/auth_api.dart';
import '../../../domain/repositories/token_provider.dart';
import '../../../shared/result.dart';

/// Coordinates authentication API calls and token persistence.
class AuthRepository {
  AuthRepository({
    required AuthApi authApi,
    required TokenProvider tokenProvider,
  })  : _authApi = authApi,
        _tokenProvider = tokenProvider;

  final AuthApi _authApi;
  final TokenProvider _tokenProvider;

  Future<Result<void>> login({
    required String email,
    required String password,
  }) async {
    final result = await _authApi.login(
      LoginRequestModel(email: email, password: password),
    );
    return result.when(
      success: (tokens) async {
        await _persistTokens(tokens);
        return const Result<void>.success(null);
      },
      failure: (err) => Result<void>.failure(err),
    );
  }

  Future<Result<void>> register({
    required String email,
    required String password,
    String? nickname,
  }) async {
    final result = await _authApi.register(
      RegisterRequestModel(
          email: email, password: password, nickname: nickname),
    );
    return result.when(
      success: (tokens) async {
        await _persistTokens(tokens);
        return const Result<void>.success(null);
      },
      failure: (err) => Result<void>.failure(err),
    );
  }

  Future<void> logout() => _tokenProvider.clearTokens();

  Future<bool> isAuthenticated() async {
    final token = await _tokenProvider.getAccessToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> _persistTokens(AuthTokenModel tokens) async {
    await _tokenProvider.setTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );
  }
}
