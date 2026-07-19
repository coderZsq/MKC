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
  const ServerException({
    this.code,
    this.traceId,
    this.retryable = false,
    String? message,
  }) : _message = message;

  final String? code;
  final String? traceId;
  final bool retryable;
  final String? _message;

  @override
  String get message =>
      _message ?? (code == null ? '服务器内部错误' : userMessageForCode(code));
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

class FilePickerFailedException extends AppException {
  const FilePickerFailedException();

  @override
  String get message => '文件选择失败';
}

class PlatformUnsupportedException extends AppException {
  const PlatformUnsupportedException();

  @override
  String get message => '当前平台暂不支持该能力';
}

class StreamDisconnectedException extends AppException {
  const StreamDisconnectedException();

  @override
  String get message => '回答连接已断开，请重试';
}

String userMessageForCode(String? code) {
  return switch (code) {
    'FILE_TOO_LARGE' || '413' => '文件超过大小限制',
    'FILE_UNSUPPORTED_TYPE' || '415' => '不支持的文件类型',
    'TASK_NOT_FOUND' || 'NOT_FOUND' => '资源不存在或已过期',
    'RETRIEVAL_TIMEOUT' => '检索超时，请稍后重试',
    'RETRIEVAL_UNAVAILABLE' => '检索服务暂不可用，请稍后重试',
    'LLM_TIMEOUT' => '模型响应超时，请稍后重试',
    'STREAM_DISCONNECTED' => '回答连接已断开，请重试',
    'PLATFORM_UNSUPPORTED' => '当前平台暂不支持该能力',
    'FILE_PICKER_FAILED' => '文件选择失败',
    'LLM_UNAVAILABLE' || 'LLM_STREAM_ERROR' => '模型服务暂不可用，请稍后重试',
    'DEPENDENCY_UNAVAILABLE' ||
    'VECTOR_STORE_UNAVAILABLE' ||
    'EMBEDDING_UNAVAILABLE' =>
      '依赖服务暂不可用，请稍后重试',
    'UNAUTHORIZED' ||
    'AUTH_INVALID_TOKEN' ||
    'AUTH_TOKEN_EXPIRED' =>
      '登录已过期，请重新登录',
    'VALIDATION_ERROR' || 'INVALID_REQUEST' => '请求参数错误',
    _ => '服务繁忙，请稍后重试',
  };
}
