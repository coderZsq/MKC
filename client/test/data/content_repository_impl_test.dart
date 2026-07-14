import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/task_api.dart';
import 'package:mkc_client/data/models/task_result_model.dart';
import 'package:mkc_client/data/repositories/content_repository_impl.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/task.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../shared/content_test_helpers.dart';

class _FakeTaskApi extends TaskApi {
  Result<TaskResultModel>? nextResult;
  String? lastResourceId;

  _FakeTaskApi() : super(client: _StubApiClient());

  @override
  Future<Result<TaskResultModel>> getResultByResourceId(
    String resourceId,
  ) async {
    lastResourceId = resourceId;
    return nextResult ??
        const Result<TaskResultModel>.failure(ServerException(code: 'UNEXPECTED'));
  }
}

class _StubApiClient extends ApiClient {
  _StubApiClient()
      : super(
          baseUrl: 'http://localhost',
          tokenProvider: _StubTokenProvider(),
        );
}

class _StubTokenProvider implements TokenProvider {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {}
}

void main() {
  group('parseSrt', () {
    test('parses valid SRT into segments', () {
      final segments = parseSrt(sampleSrt);

      expect(segments, hasLength(2));
      expect(segments[0].index, 1);
      expect(segments[0].start, const Duration(seconds: 1));
      expect(segments[0].end, const Duration(seconds: 4));
      expect(segments[0].text, 'Hello world');
      expect(segments[1].text, 'Second subtitle text');
    });

    test('ignores empty blocks and malformed entries', () {
      final segments = parseSrt('''1
00:00:01,000 --> 00:00:02,000
Keep

malformed block

2
00:00:03,000 --> 00:00:04,000
Also keep''');

      expect(segments, hasLength(2));
      expect(segments[0].text, 'Keep');
      expect(segments[1].text, 'Also keep');
    });

    test('supports period-based millisecond separator', () {
      final segments = parseSrt('''1
00:00:01.500 --> 00:00:02.250
Text''');

      expect(segments[0].start, const Duration(milliseconds: 1500));
      expect(segments[0].end, const Duration(milliseconds: 2250));
    });

    test('throws FormatException on invalid timecode', () {
      expect(
        () => parseSrt('''1
bad timecode --> 00:00:02,000
Text'''),
        throwsFormatException,
      );
    });
  });

  group('parseParsedJson', () {
    test('parses PDF JSON into pages', () {
      final pages = parseParsedJson(sampleParsedPdfJson);

      expect(pages, hasLength(2));
      expect(pages[0].pageNumber, 1);
      expect(pages[0].text, 'Page one content');
      expect(pages[0].blocks, hasLength(1));
      expect(pages[0].blocks[0].text, 'Page one content');
      expect(pages[0].blocks[0].x, 10);
      expect(pages[0].blocks[0].y, 20);
      expect(pages[1].blocks[0].text, 'Page two content');
    });

    test('throws FormatException when pages missing', () {
      expect(
        () => parseParsedJson('{"meta": "data"}'),
        throwsFormatException,
      );
    });
  });

  group('ContentRepositoryImpl', () {
    late _FakeTaskApi taskApi;
    late FakeContentRemoteDataSource remoteDataSource;
    late ContentRepositoryImpl repository;

    setUp(() {
      taskApi = _FakeTaskApi();
      remoteDataSource = FakeContentRemoteDataSource();
      repository = ContentRepositoryImpl(
        taskApi: taskApi,
        remoteDataSource: remoteDataSource,
      );
    });

    test('returns task not completed error for pending task', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(status: TaskStatus.pending),
      );

      final result = await repository.getContent('t1', ContentType.audio);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(
          success: (_) => null,
          failure: (e) => e,
        ),
        isA<TaskNotCompletedException>(),
      );
    });

    test('loads audio content from subtitle and transcript', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't1',
          subtitleUrl: 'https://example.com/sub.srt',
          transcriptUrl: 'https://example.com/trans.json',
        ),
      );
      remoteDataSource.setText('https://example.com/sub.srt', sampleSrt);
      remoteDataSource.setText(
        'https://example.com/trans.json',
        sampleTranscriptJson,
      );

      final result = await repository.getContent('t1', ContentType.audio);

      expect(taskApi.lastResourceId, 't1');
      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
      final content = result.when(
        success: (c) => c,
        failure: (_) => null,
      ) as AudioContent?;
      expect(content, isNotNull);
      expect(content!.segments, hasLength(2));
      expect(content.segments[0].text, 'Hello world');
      expect(content.segments[0].originalText, 'hello  world');
    });

    test('loads PDF content from parsed URL', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't2',
          parsedUrl: 'https://example.com/parsed.json',
        ),
      );
      remoteDataSource.setText(
        'https://example.com/parsed.json',
        sampleParsedPdfJson,
      );

      final result = await repository.getContent('t2', ContentType.pdf);

      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
      final content = result.when(
        success: (c) => c,
        failure: (_) => null,
      );
      expect(content, isA<PdfContent>());
      expect((content as PdfContent).pages, hasLength(2));
    });

    test('returns ContentParseException when subtitle URL missing', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(taskId: 't3'),
      );

      final result = await repository.getContent('t3', ContentType.audio);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<ContentParseException>(),
      );
    });

    test('returns ContentParseException when parsed URL missing', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(taskId: 't4'),
      );

      final result = await repository.getContent('t4', ContentType.pdf);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<ContentParseException>(),
      );
    });

    test('returns download error without parsing', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't5',
          parsedUrl: 'https://example.com/parsed.json',
        ),
      );
      remoteDataSource.setError(
        'https://example.com/parsed.json',
        const NetworkException(),
      );

      final result = await repository.getContent('t5', ContentType.pdf);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<NetworkException>(),
      );
    });

    test('returns ContentParseException on invalid PDF JSON', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't6',
          parsedUrl: 'https://example.com/parsed.json',
        ),
      );
      remoteDataSource.setText('https://example.com/parsed.json', 'not json');

      final result = await repository.getContent('t6', ContentType.pdf);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<ContentParseException>(),
      );
    });

    test('returns ContentParseException on invalid SRT', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't7',
          subtitleUrl: 'https://example.com/sub.srt',
        ),
      );
      remoteDataSource.setText('https://example.com/sub.srt', 'bad srt');

      final result = await repository.getContent('t7', ContentType.audio);

      expect(
        result.when(success: (_) => false, failure: (_) => true),
        isTrue,
      );
      expect(
        result.when(success: (_) => null, failure: (e) => e),
        isA<ContentParseException>(),
      );
    });

    test('falls back to SRT only when transcript download fails', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't8',
          subtitleUrl: 'https://example.com/sub.srt',
          transcriptUrl: 'https://example.com/trans.json',
        ),
      );
      remoteDataSource.setText('https://example.com/sub.srt', sampleSrt);
      remoteDataSource.setError(
        'https://example.com/trans.json',
        const NetworkException(),
      );

      final result = await repository.getContent('t8', ContentType.audio);

      final content = result.when(
        success: (c) => c as AudioContent,
        failure: (_) => null,
      );
      expect(content, isNotNull);
      expect(content!.segments[0].text, 'Hello world');
      expect(content.segments[0].originalText, isNull);
    });

    test('falls back to SRT when transcript JSON is malformed', () async {
      taskApi.nextResult = Result.success(
        createTaskResultModel(
          taskId: 't9',
          subtitleUrl: 'https://example.com/sub.srt',
          transcriptUrl: 'https://example.com/trans.json',
        ),
      );
      remoteDataSource.setText('https://example.com/sub.srt', sampleSrt);
      remoteDataSource.setText(
        'https://example.com/trans.json',
        '{"segments":[{"start":1,"end":4,"original_text":123}]}',
      );

      final result = await repository.getContent('t9', ContentType.audio);

      final content = result.when(
        success: (c) => c as AudioContent,
        failure: (_) => null,
      );
      expect(content, isNotNull);
      expect(content!.segments[0].text, 'Hello world');
      expect(content.segments[0].originalText, isNull);
    });
  });
}
