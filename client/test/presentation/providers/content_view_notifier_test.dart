import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/parsed_page.dart';
import 'package:mkc_client/domain/entities/subtitle_segment.dart';
import 'package:mkc_client/presentation/providers/content_view_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/content_test_helpers.dart';

AudioContent _sampleAudioContent() {
  return const AudioContent(
    taskId: 't1',
    segments: [
      SubtitleSegment(
        index: 1,
        start: Duration(seconds: 1),
        end: Duration(seconds: 4),
        text: 'Hello world',
        originalText: 'Original transcript',
      ),
      SubtitleSegment(
        index: 2,
        start: Duration(seconds: 5),
        end: Duration(seconds: 7),
        text: 'World again',
      ),
    ],
  );
}

PdfContent _samplePdfContent() {
  return const PdfContent(
    taskId: 't1',
    pages: [
      ParsedPage(pageNumber: 1, text: 'First page'),
      ParsedPage(pageNumber: 2, text: 'Second page'),
    ],
  );
}

void main() {
  group('ContentViewNotifier', () {
    late FakeContentRepository repository;
    late ContentViewNotifier notifier;

    setUp(() {
      repository = FakeContentRepository();
      notifier = ContentViewNotifier(
        repository: repository,
        resourceId: 't1',
        contentType: ContentType.audio,
      );
    });

    tearDown(() {
      notifier.dispose();
    });

    test('load sets content on success', () async {
      repository.nextResult = Result.success(_sampleAudioContent());

      await notifier.load();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, isNull);
      expect(notifier.state.content, isA<AudioContent>());
      expect(repository.lastResourceId, 't1');
      expect(repository.lastContentType, ContentType.audio);
    });

    test('load sets error on failure', () async {
      repository.nextError = const NetworkException();

      await notifier.load();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, isA<NetworkException>());
      expect(notifier.state.content, isNull);
    });

    test('retry reloads content', () async {
      repository.nextError = const NetworkException();
      await notifier.load();
      expect(notifier.state.error, isNotNull);

      repository.nextError = null;
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.retry();

      expect(notifier.state.error, isNull);
      expect(notifier.state.content, isNotNull);
      expect(repository.callCount, 2);
    });

    test('search debounce builds matches', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();

      notifier.onSearchChanged('world');
      expect(notifier.state.keyword, isEmpty);
      await Future.delayed(const Duration(milliseconds: 350));

      expect(notifier.state.keyword, 'world');
      expect(notifier.state.matches, hasLength(2));
      expect(notifier.state.currentMatchIndex, 0);
    });

    test('search is case-insensitive', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();

      notifier.onSearchChanged('HELLO');
      await Future.delayed(const Duration(milliseconds: 350));

      expect(notifier.state.matches, hasLength(1));
      expect(notifier.state.matches.first.startOffset, 0);
    });

    test('search offsets are based on original text', () async {
      repository.nextResult = const Result.success(
        AudioContent(
          taskId: 't1',
          segments: [
            SubtitleSegment(
              index: 1,
              start: Duration(seconds: 1),
              end: Duration(seconds: 4),
              text: 'Hello WORLD',
            ),
          ],
        ),
      );
      await notifier.load();

      notifier.onSearchChanged('world');
      await Future.delayed(const Duration(milliseconds: 350));

      final match = notifier.state.matches.single;
      expect(match.startOffset, 6);
      expect(match.endOffset, 11);
    });

    test('jumpToNextMatch cycles through matches', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();
      notifier.onSearchChanged('world');
      await Future.delayed(const Duration(milliseconds: 350));
      expect(notifier.state.currentMatchIndex, 0);

      notifier.jumpToNextMatch();
      expect(notifier.state.currentMatchIndex, 1);

      notifier.jumpToNextMatch();
      expect(notifier.state.currentMatchIndex, 0);
    });

    test('jumpToPreviousMatch cycles backwards', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();
      notifier.onSearchChanged('world');
      await Future.delayed(const Duration(milliseconds: 350));
      expect(notifier.state.currentMatchIndex, 0);

      notifier.jumpToPreviousMatch();
      expect(notifier.state.currentMatchIndex, 1);
    });

    test('toggleTextMode switches showCleanedText and refreshes search', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();
      notifier.onSearchChanged('original');
      await Future.delayed(const Duration(milliseconds: 350));
      expect(notifier.state.matches, hasLength(0));

      notifier.toggleTextMode();
      await Future.delayed(const Duration(milliseconds: 350));

      expect(notifier.state.showCleanedText, isFalse);
      expect(notifier.state.matches, hasLength(1));
    });

    test('toggleTextMode without active search does not crash', () async {
      repository.nextResult = Result.success(_sampleAudioContent());
      await notifier.load();

      notifier.toggleTextMode();

      expect(notifier.state.showCleanedText, isFalse);
      expect(notifier.state.matches, isEmpty);
    });

    test('togglePageExpanded adds and removes page numbers', () async {
      repository.nextResult = Result.success(_samplePdfContent());
      await notifier.load();

      // First page is expanded by default.
      expect(notifier.state.expandedPageNumbers, contains(1));

      notifier.togglePageExpanded(1);
      expect(notifier.state.expandedPageNumbers, isNot(contains(1)));

      notifier.togglePageExpanded(2);
      expect(notifier.state.expandedPageNumbers, contains(2));

      notifier.togglePageExpanded(1);
      expect(notifier.state.expandedPageNumbers, contains(1));

      notifier.togglePageExpanded(1);
      expect(notifier.state.expandedPageNumbers, isNot(contains(1)));
    });

    test('search on PDF content matches across pages', () async {
      repository.nextResult = Result.success(_samplePdfContent());
      await notifier.load();

      notifier.onSearchChanged('page');
      await Future.delayed(const Duration(milliseconds: 350));

      expect(notifier.state.matches, hasLength(2));
      expect(
        notifier.state.matches.map((m) => m.itemIndex).toSet(),
        {0, 1},
      );
    });

    test('jumpToNextMatch expands the PDF page containing the match', () async {
      repository.nextResult = Result.success(_samplePdfContent());
      await notifier.load();

      notifier.onSearchChanged('page');
      await Future.delayed(const Duration(milliseconds: 350));
      expect(notifier.state.expandedPageNumbers, contains(1));

      notifier.jumpToNextMatch();

      expect(notifier.state.currentMatchIndex, 1);
      expect(notifier.state.expandedPageNumbers, contains(2));
    });

    test('dispose cancels active debounce timer', () async {
      final repo = FakeContentRepository();
      repo.nextResult = Result.success(_sampleAudioContent());
      final n = ContentViewNotifier(
        repository: repo,
        resourceId: 't1',
        contentType: ContentType.audio,
      );
      await n.load();

      n.onSearchChanged('query');
      n.dispose();

      await Future.delayed(const Duration(milliseconds: 350));
      // No exception is thrown because the debounce callback checks mounted.
      expect(true, isTrue);
    });
  });
}
