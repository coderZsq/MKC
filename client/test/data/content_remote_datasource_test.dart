import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/content_remote_datasource.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';

const _expectedHost = 'minio.example.com';

void main() {
  group('ContentRemoteDataSource', () {
    ContentRemoteDataSource createDataSource({Dio? dio}) {
      return ContentRemoteDataSource(
        dio: dio,
        expectedHost: _expectedHost,
      );
    }

    test('returns text for a valid signed URL', () async {
      final dio = Dio();
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            handler.resolve(
              Response(
                requestOptions: options,
                data: 'file content',
                statusCode: 200,
              ),
            );
          },
        ),
      );
      final dataSource = createDataSource(dio: dio);

      final result = await dataSource.downloadText(
        'https://minio.example.com/file.srt',
      );

      expect(
        result.when(success: (text) => text, failure: (_) => ''),
        'file content',
      );
    });

    test('rejects non-HTTP schemes', () async {
      final dataSource = createDataSource();

      final result =
          await dataSource.downloadText('ftp://example.com/file.srt');

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<UnsafeUrlException>(),
      );
    });

    test('rejects host mismatch', () async {
      final dataSource = createDataSource();

      final result = await dataSource.downloadText(
        'https://attacker.example.com/file.srt',
      );

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<UnsafeUrlException>(),
      );
    });

    test('allows HTTP URLs when expected host is empty', () async {
      final dio = Dio();
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            handler.resolve(
              Response(
                requestOptions: options,
                data: 'local content',
                statusCode: 200,
              ),
            );
          },
        ),
      );
      final dataSource = ContentRemoteDataSource(
        dio: dio,
        expectedHost: '',
      );

      final result = await dataSource.downloadText(
        'http://localhost:9000/file.srt',
      );

      expect(
        result.when(success: (text) => text, failure: (_) => ''),
        'local content',
      );
    });

    test('caches subsequent downloads for the same URL', () async {
      final dio = Dio();
      var requestCount = 0;
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            requestCount++;
            handler.resolve(
              Response(
                requestOptions: options,
                data: 'cached content',
                statusCode: 200,
              ),
            );
          },
        ),
      );
      final dataSource = createDataSource(dio: dio);
      const url = 'https://minio.example.com/file.srt';

      await dataSource.downloadText(url);
      await dataSource.downloadText(url);

      expect(requestCount, 1);
    });

    test('does not follow HTTP redirects', () async {
      final dio = Dio();
      var requestCount = 0;
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            requestCount++;
            handler.resolve(
              Response(
                requestOptions: options,
                data: '',
                statusCode: 302,
                headers: Headers.fromMap({
                  'location': ['https://minio.example.com/redirected'],
                }),
              ),
            );
          },
        ),
      );
      final dataSource = createDataSource(dio: dio);

      await dataSource.downloadText('https://minio.example.com/file.srt');

      expect(requestCount, 1);
    });

    group('Dio exception mapping', () {
      Future<AppException> downloadWithDioException(
        DioException exception,
      ) async {
        final dio = Dio();
        dio.interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) {
              handler.reject(exception, true);
            },
          ),
        );
        final dataSource = createDataSource(dio: dio);
        final result = await dataSource.downloadText(
          'https://minio.example.com/file.srt',
        );
        return result.when(
          success: (_) => throw StateError('expected failure'),
          failure: (e) => e,
        );
      }

      DioException buildException(
        DioExceptionType type, {
        int? statusCode,
      }) {
        return DioException(
          requestOptions: RequestOptions(path: '/file.srt'),
          type: type,
          response: statusCode == null
              ? null
              : Response(
                  requestOptions: RequestOptions(path: '/file.srt'),
                  statusCode: statusCode,
                ),
        );
      }

      test('maps connection timeout to NetworkException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.connectionTimeout),
        );
        expect(exception, isA<NetworkException>());
      });

      test('maps connection error to NetworkException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.connectionError),
        );
        expect(exception, isA<NetworkException>());
      });

      test('maps 401 bad response to UnauthorizedException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.badResponse, statusCode: 401),
        );
        expect(exception, isA<UnauthorizedException>());
      });

      test('maps 500 bad response to ServerException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.badResponse, statusCode: 500),
        );
        expect(exception, isA<ServerException>());
        expect(
          (exception as ServerException).code,
          '500',
        );
      });

      test('maps cancel to UnknownException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.cancel),
        );
        expect(exception, isA<UnknownException>());
      });

      test('maps unknown to UnknownException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.unknown),
        );
        expect(exception, isA<UnknownException>());
      });

      test('maps transform timeout to UnknownException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.transformTimeout),
        );
        expect(exception, isA<UnknownException>());
      });

      test('maps bad certificate to NetworkException', () async {
        final exception = await downloadWithDioException(
          buildException(DioExceptionType.badCertificate),
        );
        expect(exception, isA<NetworkException>());
      });
    });
  });
}
