import 'package:mkc_client/data/datasources/remote/content_remote_datasource.dart';
import 'package:mkc_client/data/models/task_result_model.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/task.dart';
import 'package:mkc_client/domain/repositories/content_repository.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

/// Builds a fake [TaskResultModel] for completed tasks.
TaskResultModel createTaskResultModel({
  String taskId = 'task-1',
  TaskStatus status = TaskStatus.completed,
  String? transcriptUrl,
  String? subtitleUrl,
  String? parsedUrl,
}) {
  return TaskResultModel(
    taskId: taskId,
    status: status,
    files: ResultFiles(
      transcriptUrl: transcriptUrl,
      subtitleUrl: subtitleUrl,
      parsedUrl: parsedUrl,
    ),
  );
}

/// A fake content repository with controllable responses for tests.
class FakeContentRepository implements ContentRepository {
  Result<Content>? nextResult;
  AppException? nextError;
  Duration delay = Duration.zero;
  String? lastResourceId;
  ContentType? lastContentType;
  int callCount = 0;

  @override
  Future<Result<Content>> getContent(
    String resourceId,
    ContentType contentType,
  ) async {
    callCount++;
    lastResourceId = resourceId;
    lastContentType = contentType;
    if (delay != Duration.zero) {
      await Future.delayed(delay);
    }
    if (nextError != null) {
      return Result<Content>.failure(nextError!);
    }
    return nextResult ??
        const Result<Content>.failure(
          ServerException(code: 'UNEXPECTED'),
        );
  }
}

/// Fake remote data source that returns preset text for each URL.
class FakeContentRemoteDataSource implements ContentRemoteDataSource {
  final Map<String, String> _urlToText = {};
  final Map<String, AppException> _urlToError = {};

  void setText(String url, String text) {
    _urlToText[url] = text;
  }

  void setError(String url, AppException error) {
    _urlToError[url] = error;
  }

  @override
  Future<Result<String>> downloadText(String url) async {
    final error = _urlToError[url];
    if (error != null) {
      return Result<String>.failure(error);
    }
    return Result<String>.success(_urlToText[url] ?? '');
  }
}

/// A sample valid SRT string with two segments.
const sampleSrt = '''1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,500 --> 00:00:07,200
Second subtitle text'''
;

/// A sample transcript JSON matching the S2-3 structure.
const sampleTranscriptJson = '''{
  "segments": [
    {"start": 1, "end": 4, "text": "Hello world", "original_text": "hello  world"},
    {"start": 5.5, "end": 7.2, "text": "Second subtitle text", "original_text": "Second subtitle text"}
  ]
}'''
;

/// A sample PDF parsed JSON matching the S2-4 structure.
const sampleParsedPdfJson = '''{
  "pages": [
    {
      "page_number": 1,
      "text": "Page one content",
      "blocks": [{"text": "Page one content", "x": 10, "y": 20}]
    },
    {
      "page_number": 2,
      "text": "Page two content",
      "blocks": ["Page two content"]
    }
  ]
}'''
;
