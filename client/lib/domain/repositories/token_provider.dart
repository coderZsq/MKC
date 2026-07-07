/// Abstract source for access/refresh tokens.
abstract interface class TokenProvider {
  Future<String?> getAccessToken();

  Future<bool> refreshAccessToken();

  Future<void> clearTokens();
}
