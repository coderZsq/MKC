// ignore_for_file: prefer_const_constructors

import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';

void main() {
  group('AppException', () {
    test('new content exceptions have expected messages', () {
      expect(const TaskNotCompletedException().message, '处理中，请稍后');
      expect(const ContentParseException().message, '内容格式错误');
      expect(const UnsafeUrlException().message, '不安全的文件地址');
    });

    test('existing exceptions retain expected messages', () {
      expect(const NetworkException().message, '网络连接失败，请检查网络');
      expect(const ServerException().message, '服务器内部错误');
      expect(const UnauthorizedException().message, '登录已过期，请重新登录');
      expect(const UnknownException().message, '未知错误');
      expect(const CancelledUploadException().message, '上传已取消');
      expect(const FileSizeLimitException().message, '文件超过当前平台大小限制');
      expect(const UnsupportedFileTypeException().message, '不支持的文件类型');
      expect(
        const ValidationException({'email': 'required'}).errors['email'],
        'required',
      );
      expect(
        const ValidationException({'email': 'required'}).message,
        '请求参数错误',
      );
    });

    test('ServerException carries code', () {
      expect(const ServerException(code: 'ERR_500').code, 'ERR_500');
      expect(const ServerException().code, isNull);
    });

    test('ServerException maps known codes to friendly messages', () {
      const error = ServerException(
        code: 'LLM_TIMEOUT',
        traceId: 'trace-1',
        retryable: true,
      );

      expect(error.message, '模型响应超时，请稍后重试');
      expect(error.traceId, 'trace-1');
      expect(error.retryable, isTrue);
    });

    test('non-const constructors execute for coverage', () {
      final exceptions = <AppException>[
        NetworkException(),
        ServerException(code: '500'),
        UnauthorizedException(),
        ValidationException({'x': 'y'}),
        UnknownException(),
        CancelledUploadException(),
        TaskNotCompletedException(),
        ContentParseException(),
        UnsafeUrlException(),
        FileSizeLimitException(),
        UnsupportedFileTypeException(),
      ];
      for (final e in exceptions) {
        expect(e.message, isNotEmpty);
      }
    });
  });
}
