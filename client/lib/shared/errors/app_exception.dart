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
  const ServerException({this.code, String? message})
      : _message = message;

  final String? code;
  final String? _message;

  @override
  String get message => _message ?? '服务器内部错误';
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

class CancelledUploadException extends AppException {
  const CancelledUploadException();

  @override
  String get message => '上传已取消';
}

class TaskNotCompletedException extends AppException {
  const TaskNotCompletedException();

  @override
  String get message => '处理中，请稍后';
}

class ContentParseException extends AppException {
  const ContentParseException();

  @override
  String get message => '内容格式错误';
}

class UnsafeUrlException extends AppException {
  const UnsafeUrlException();

  @override
  String get message => '不安全的文件地址';
}

class FileSizeLimitException extends AppException {
  const FileSizeLimitException();

  @override
  String get message => '文件超过当前平台大小限制';
}

class UnsupportedFileTypeException extends AppException {
  const UnsupportedFileTypeException();

  @override
  String get message => '不支持的文件类型';
}
