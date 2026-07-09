import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/parsed_page.dart';
import 'package:mkc_client/domain/entities/subtitle_segment.dart';

void main() {
  group('SubtitleSegment', () {
    test('returns cleaned text by default', () {
      const segment = SubtitleSegment(
        index: 1,
        start: Duration(seconds: 1),
        end: Duration(seconds: 2),
        text: 'cleaned',
        originalText: 'original',
      );

      expect(segment.displayText(showCleaned: true), 'cleaned');
      expect(segment.displayText(showCleaned: false), 'original');
    });

    test('falls back to cleaned text when original is missing', () {
      const segment = SubtitleSegment(
        index: 1,
        start: Duration(seconds: 1),
        end: Duration(seconds: 2),
        text: 'cleaned',
      );

      expect(segment.displayText(showCleaned: false), 'cleaned');
    });

    test('copyWith creates a new instance with updated values', () {
      const segment = SubtitleSegment(
        index: 1,
        start: Duration(seconds: 1),
        end: Duration(seconds: 2),
        text: 'cleaned',
      );

      final updated = segment.copyWith(text: 'new text');

      expect(updated.text, 'new text');
      expect(updated.index, segment.index);
      expect(segment.text, 'cleaned');
    });
  });

  group('ParsedPage', () {
    test('copyWith updates text immutably', () {
      const page = ParsedPage(pageNumber: 1, text: 'old');

      final updated = page.copyWith(text: 'new');

      expect(updated.text, 'new');
      expect(page.text, 'old');
    });
  });

  group('Content', () {
    test('AudioContent carries audio type and segments', () {
      const content = AudioContent(
        taskId: 't1',
        segments: [
          SubtitleSegment(
            index: 1,
            start: Duration.zero,
            end: Duration(seconds: 1),
            text: 'hello',
          ),
        ],
      );

      expect(content.type, ContentType.audio);
      expect(content.segments, hasLength(1));

      final updated = content.copyWith(taskId: 't2');
      expect(updated.taskId, 't2');
      expect(updated.segments, content.segments);
    });

    test('PdfContent carries pdf type and pages', () {
      const content = PdfContent(
        taskId: 't1',
        pages: [ParsedPage(pageNumber: 1, text: 'page one')],
      );

      expect(content.type, ContentType.pdf);
      expect(content.pages, hasLength(1));

      final updated = content.copyWith(
        pages: const [
          ParsedPage(pageNumber: 1, text: 'page one'),
          ParsedPage(pageNumber: 2, text: 'page two'),
        ],
      );
      expect(updated.pages, hasLength(2));
      expect(content.pages, hasLength(1));
    });
  });
}
