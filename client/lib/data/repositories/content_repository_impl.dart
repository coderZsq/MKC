import 'dart:convert';

import '../../../domain/entities/content.dart';
import '../../../domain/entities/content_type.dart';
import '../../../domain/entities/parsed_page.dart';
import '../../../domain/entities/subtitle_segment.dart';
import '../../../domain/entities/task.dart';
import '../../../domain/repositories/content_repository.dart';
import '../../../shared/errors/app_exception.dart';
import '../../../shared/result.dart';
import '../datasources/remote/content_remote_datasource.dart';
import '../datasources/remote/task_api.dart';
import '../models/task_result_model.dart';

/// Coordinates result API calls and parses SRT/JSON files into domain content.
class ContentRepositoryImpl implements ContentRepository {
  ContentRepositoryImpl({
    required TaskApi taskApi,
    required ContentRemoteDataSource remoteDataSource,
  })  : _taskApi = taskApi,
        _remoteDataSource = remoteDataSource;

  final TaskApi _taskApi;
  final ContentRemoteDataSource _remoteDataSource;

  @override
  Future<Result<Content>> getContent(
    String resourceId,
    ContentType contentType,
  ) async {
    final result = await _taskApi.getResultByResourceId(resourceId);
    return result.when(
      success: (taskResult) async => _loadTaskResult(taskResult, contentType),
      failure: (error) => Result<Content>.failure(error),
    );
  }

  Future<Result<Content>> _loadTaskResult(
    TaskResultModel taskResult,
    ContentType contentType,
  ) async {
    if (taskResult.status != TaskStatus.completed) {
      return const Result<Content>.failure(
        TaskNotCompletedException(),
      );
    }

    return switch (contentType) {
      ContentType.audio => _loadAudio(taskResult),
      ContentType.pdf => _loadPdf(taskResult),
    };
  }

  Future<Result<Content>> _loadAudio(TaskResultModel taskResult) async {
    final subtitleUrl = taskResult.files.subtitleUrl;
    if (subtitleUrl == null || subtitleUrl.isEmpty) {
      return const Result<Content>.failure(ContentParseException());
    }

    final subtitleResult = await _remoteDataSource.downloadText(subtitleUrl);
    final segments = await subtitleResult.when(
      success: (srt) async => _parseSrtWithTranscript(srt, taskResult.files.transcriptUrl),
      failure: (error) => Future<Result<List<SubtitleSegment>>>.value(
        Result<List<SubtitleSegment>>.failure(error),
      ),
    );

    return segments.when(
      success: (list) => Result<Content>.success(
        AudioContent(taskId: taskResult.taskId, segments: list),
      ),
      failure: (error) => Result<Content>.failure(error),
    );
  }

  Future<Result<List<SubtitleSegment>>> _parseSrtWithTranscript(
    String srt,
    String? transcriptUrl,
  ) async {
    try {
      final srtSegments = parseSrt(srt);
      if (transcriptUrl == null || transcriptUrl.isEmpty) {
        return Result<List<SubtitleSegment>>.success(srtSegments);
      }
      final transcriptResult = await _remoteDataSource.downloadText(transcriptUrl);
      return transcriptResult.when(
        success: (json) {
          try {
            return Result<List<SubtitleSegment>>.success(
              _mergeTranscript(srtSegments, json),
            );
          } catch (_) {
            return Result<List<SubtitleSegment>>.success(srtSegments);
          }
        },
        failure: (error) => Result<List<SubtitleSegment>>.success(srtSegments),
      );
    } on FormatException {
      return const Result<List<SubtitleSegment>>.failure(ContentParseException());
    }
  }

  Future<Result<Content>> _loadPdf(TaskResultModel taskResult) async {
    final parsedUrl = taskResult.files.parsedUrl;
    if (parsedUrl == null || parsedUrl.isEmpty) {
      return const Result<Content>.failure(ContentParseException());
    }

    final downloadResult = await _remoteDataSource.downloadText(parsedUrl);
    return downloadResult.when(
      success: (json) {
        try {
          final pages = parseParsedJson(json);
          return Result<Content>.success(
            PdfContent(taskId: taskResult.taskId, pages: pages),
          );
        } on FormatException {
          return const Result<Content>.failure(ContentParseException());
        }
      },
      failure: (error) => Result<Content>.failure(error),
    );
  }
}

/// Parses an SRT string into a list of [SubtitleSegment].
List<SubtitleSegment> parseSrt(String srt) {
  final segments = <SubtitleSegment>[];
  final blocks = srt.split('\n\n');
  for (final block in blocks) {
    final segment = _parseSrtBlock(block.trim());
    if (segment != null) {
      segments.add(segment);
    }
  }
  if (srt.trim().isNotEmpty && segments.isEmpty) {
    throw const FormatException('No valid SRT segments found');
  }
  return segments;
}

SubtitleSegment? _parseSrtBlock(String block) {
  if (block.isEmpty) return null;
  final lines = block.split('\n');
  if (lines.length < 3) return null;

  final indexValue = int.tryParse(lines[0].trim());
  if (indexValue == null) {
    throw const FormatException('Invalid subtitle index');
  }
  final timeLine = lines[1];
  final arrowIndex = timeLine.indexOf(' --> ');
  if (arrowIndex == -1) return null;

  final start = _parseTimecode(timeLine.substring(0, arrowIndex));
  final end = _parseTimecode(timeLine.substring(arrowIndex + 5));
  final text = lines.sublist(2).join('\n').trim();

  return SubtitleSegment(
    index: indexValue,
    start: start,
    end: end,
    text: text,
  );
}

Duration _parseTimecode(String timecode) {
  final normalized = timecode.trim().replaceAll('.', ',');
  final parts = normalized.split(':');
  if (parts.length != 3) throw const FormatException('Invalid timecode');

  final hours = int.parse(parts[0]);
  final minutes = int.parse(parts[1]);
  final secondsAndMillis = parts[2].split(',');
  final seconds = int.parse(secondsAndMillis[0]);
  final millis = secondsAndMillis.length > 1 ? int.parse(secondsAndMillis[1]) : 0;

  return Duration(
    hours: hours,
    minutes: minutes,
    seconds: seconds,
    milliseconds: millis,
  );
}

List<SubtitleSegment> _mergeTranscript(
  List<SubtitleSegment> srtSegments,
  String transcriptJson,
) {
  final originalByTime = _buildOriginalTextMap(transcriptJson);
  if (originalByTime.isEmpty) return srtSegments;

  return srtSegments.map((segment) {
    final key = _timeKey(segment.start, segment.end);
    final original = originalByTime[key];
    if (original == null || original == segment.text) return segment;
    return segment.copyWith(originalText: original);
  }).toList();
}

Map<String, String> _buildOriginalTextMap(String transcriptJson) {
  try {
    final decoded = jsonDecode(transcriptJson) as Map<String, dynamic>?;
    final segments = decoded?['segments'] as List<dynamic>?;
    if (segments == null) return const {};

    final map = <String, String>{};
    for (final item in segments) {
      final raw = item as Map<String, dynamic>?;
      if (raw == null) continue;
      final start = _parseSeconds(raw['start']);
      final end = _parseSeconds(raw['end']);
      final text = (raw['original_text'] ?? raw['text']) as String?;
      if (text != null) {
        map[_timeKey(start, end)] = text.trim();
      }
    }
    return map;
  } on FormatException {
    return const {};
  }
}

Duration _parseSeconds(dynamic value) {
  if (value is int) return Duration(seconds: value);
  if (value is double) {
    final millis = (value * 1000).round();
    return Duration(milliseconds: millis);
  }
  return Duration.zero;
}

String _timeKey(Duration start, Duration end) {
  return '${start.inMilliseconds}:${end.inMilliseconds}';
}

/// Parses a PDF result JSON string into a list of [ParsedPage].
List<ParsedPage> parseParsedJson(String json) {
  final decoded = jsonDecode(json) as Map<String, dynamic>?;
  final pages = decoded?['pages'] as List<dynamic>?;
  if (pages == null) throw const FormatException('Missing pages');

  return pages.map(_parseParsedPage).toList();
}

ParsedPage _parseParsedPage(dynamic item) {
  final raw = item as Map<String, dynamic>?;
  if (raw == null) throw const FormatException('Invalid page');

  final pageNumber = raw['page_number'] as int? ?? 0;
  final text = raw['text'] as String? ?? '';
  final blocks = _parseBlocks(raw['blocks'] as List<dynamic>?);

  return ParsedPage(pageNumber: pageNumber, text: text, blocks: blocks);
}

List<ParsedBlock> _parseBlocks(List<dynamic>? rawBlocks) {
  if (rawBlocks == null) return const [];
  return rawBlocks.map(_parseParsedBlock).toList();
}

ParsedBlock _parseParsedBlock(dynamic item) {
  if (item is String) return ParsedBlock(text: item);
  final raw = item as Map<String, dynamic>? ?? const {};
  final text = raw['text'] as String? ?? '';
  return ParsedBlock(
    text: text,
    x: (raw['x'] as num?)?.toDouble(),
    y: (raw['y'] as num?)?.toDouble(),
    width: (raw['width'] as num?)?.toDouble(),
    height: (raw['height'] as num?)?.toDouble(),
  );
}
