import 'content_type.dart';
import 'parsed_page.dart';
import 'subtitle_segment.dart';

/// Base class for loaded task content.
sealed class Content {
  const Content({required this.taskId, required this.type});

  final String taskId;
  final ContentType type;
}

/// Loaded audio content represented by SRT subtitle segments.
class AudioContent extends Content {
  const AudioContent({
    required super.taskId,
    required this.segments,
  }) : super(type: ContentType.audio);

  final List<SubtitleSegment> segments;

  AudioContent copyWith({
    String? taskId,
    List<SubtitleSegment>? segments,
  }) {
    return AudioContent(
      taskId: taskId ?? this.taskId,
      segments: segments ?? this.segments,
    );
  }
}

/// Loaded PDF content represented by parsed pages.
class PdfContent extends Content {
  const PdfContent({
    required super.taskId,
    required this.pages,
  }) : super(type: ContentType.pdf);

  final List<ParsedPage> pages;

  PdfContent copyWith({
    String? taskId,
    List<ParsedPage>? pages,
  }) {
    return PdfContent(
      taskId: taskId ?? this.taskId,
      pages: pages ?? this.pages,
    );
  }
}
