import '../../shared/errors/app_exception.dart';

/// Maps application exceptions to user-facing messages for the upload flow.
String mapUploadErrorToMessage(AppException? error) {
  return switch (error) {
    NetworkException _ => '网络异常，请检查连接',
    UnauthorizedException _ => '登录已过期，请重新登录',
    FileSizeLimitException _ => '文件超过当前平台大小限制',
    UnsupportedFileTypeException _ => '不支持的文件类型',
    FilePickerFailedException _ => '文件选择失败，请重试',
    PlatformUnsupportedException _ => '当前平台暂不支持文件选择',
    ServerException(:final code)
        when code == 'FILE_TOO_LARGE' || code == '413' =>
      '文件过大，请重新选择',
    ServerException(:final code)
        when code == 'FILE_UNSUPPORTED_TYPE' || code == '415' =>
      '服务器不支持该文件类型',
    ServerException _ => '上传失败，请稍后重试',
    UnknownException _ => '上传失败，请稍后重试',
    _ => '上传失败，请稍后重试',
  };
}
