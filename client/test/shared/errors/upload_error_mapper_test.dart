import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/errors/upload_error_mapper.dart';

void main() {
  group('mapUploadErrorToMessage', () {
    test('maps NetworkException', () {
      expect(
        mapUploadErrorToMessage(const NetworkException()),
        '网络异常，请检查连接',
      );
    });

    test('maps UnauthorizedException', () {
      expect(
        mapUploadErrorToMessage(const UnauthorizedException()),
        '登录已过期，请重新登录',
      );
    });

    test('maps FileSizeLimitException', () {
      expect(
        mapUploadErrorToMessage(const FileSizeLimitException()),
        '文件超过当前平台大小限制',
      );
    });

    test('maps UnsupportedFileTypeException', () {
      expect(
        mapUploadErrorToMessage(const UnsupportedFileTypeException()),
        '不支持的文件类型',
      );
    });

    test('maps server FILE_TOO_LARGE', () {
      expect(
        mapUploadErrorToMessage(const ServerException(code: 'FILE_TOO_LARGE')),
        '文件过大，请重新选择',
      );
    });

    test('maps server 413', () {
      expect(
        mapUploadErrorToMessage(const ServerException(code: '413')),
        '文件过大，请重新选择',
      );
    });

    test('maps server FILE_UNSUPPORTED_TYPE', () {
      expect(
        mapUploadErrorToMessage(
          const ServerException(code: 'FILE_UNSUPPORTED_TYPE'),
        ),
        '服务器不支持该文件类型',
      );
    });

    test('maps server 415', () {
      expect(
        mapUploadErrorToMessage(const ServerException(code: '415')),
        '服务器不支持该文件类型',
      );
    });

    test('maps generic server error', () {
      expect(
        mapUploadErrorToMessage(const ServerException(code: 'INTERNAL_ERROR')),
        '上传失败，请稍后重试',
      );
    });

    test('maps UnknownException', () {
      expect(
        mapUploadErrorToMessage(const UnknownException()),
        '上传失败，请稍后重试',
      );
    });

    test('maps null to fallback', () {
      expect(mapUploadErrorToMessage(null), '上传失败，请稍后重试');
    });
  });
}
