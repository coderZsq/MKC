/// Base class for all application-level exceptions.
sealed class AppException implements Exception {
  const AppException();

  String get message;
}

class NetworkException extends AppException {
  const NetworkException();

  @override
  String get message => '网络连接失败，请检查网络';
}

class ServerException extends AppException {
  const ServerException({this.code});

  final String? code;

  @override
  String get message => '服务器内部错误';
}

class UnauthorizedException extends AppException {
  const UnauthorizedException();

  @override
  String get message => '登录已过期，请重新登录';
}

class ValidationException extends AppException {
  const ValidationException(this.errors);

  final Map<String, String> errors;

  @override
  String get message => '请求参数错误';
}

class UnknownException extends AppException {
  const UnknownException();

  @override
  String get message => '未知错误';
}
