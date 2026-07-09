/// Environment configuration loaded at compile time via `--dart-define`.
abstract final class Env {
  static const String environment = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'dev',
  );

  static const String _devBaseUrl = 'http://mkc.local/api/v1';
  static const String _prodBaseUrl = 'https://mkc.prod/api/v1';

  static const String baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: String.fromEnvironment(
          'APP_ENV',
          defaultValue: 'dev',
        ) ==
        'prod'
    ? _prodBaseUrl
    : _devBaseUrl,
  );

  static bool get isDev => environment == 'dev';
  static bool get isProd => environment == 'prod';

  /// Expected host for result-file signed URLs (e.g. `minio.example.com`).
  /// When empty, only the URL scheme is validated.
  static const String storageHost = String.fromEnvironment('STORAGE_HOST');
}
