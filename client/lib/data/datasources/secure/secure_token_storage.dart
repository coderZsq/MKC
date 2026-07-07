import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../domain/repositories/token_provider.dart';

/// Secure storage backed implementation of [TokenProvider].
class SecureTokenStorage implements TokenProvider {
  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

  final FlutterSecureStorage _storage;
  String? _memoryAccessToken;

  @override
  Future<String?> getAccessToken() async {
    _memoryAccessToken ??= await _storage.read(key: _accessTokenKey);
    return _memoryAccessToken;
  }

  @override
  Future<bool> refreshAccessToken() async {
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    if (refreshToken == null) {
      return false;
    }

    // TODO(S1): call POST /auth/refresh and update stored tokens.
    return true;
  }

  @override
  Future<void> clearTokens() async {
    _memoryAccessToken = null;
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  Future<void> setTokens({required String accessToken, required String refreshToken}) async {
    _memoryAccessToken = accessToken;
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }
}
