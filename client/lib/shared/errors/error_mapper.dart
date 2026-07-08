import 'app_exception.dart';

/// Maps application exceptions to user-facing messages.
String mapAuthErrorToMessage(AppException? error) {
  return switch (error) {
    NetworkException _ => '网络异常，请检查连接',
    UnauthorizedException _ => '邮箱或密码错误',
    ServerException(:final code) when code == 'CONFLICT' => '邮箱已被注册',
    ServerException _ => '服务繁忙，请稍后重试',
    UnknownException _ => '发生未知错误，请重试',
    _ => '发生未知错误，请重试',
  };
}
