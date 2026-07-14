import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/content.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/parsed_page.dart';
import 'package:mkc_client/domain/entities/subtitle_segment.dart';
import 'package:mkc_client/domain/services/audio_seek_service.dart';
import 'package:mkc_client/presentation/pages/content_view_page.dart';
import 'package:mkc_client/presentation/providers/content_view_provider.dart';
import 'package:mkc_client/presentation/widgets/pdf_text_view.dart';
import 'package:mkc_client/presentation/widgets/srt_list_view.dart';
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

class _FakeAudioSeekService implements AudioSeekService {
  Duration? lastPosition;

  @override
  void seek(Duration position) {
    lastPosition = position;
  }
}

Future<void> _pumpContentViewPage(
  WidgetTester tester, {
  required String resourceId,
  required ContentType contentType,
  FakeContentRepository? repository,
  AudioSeekService? audioSeekService,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        contentRepositoryProvider.overrideWithValue(
          repository ?? FakeContentRepository(),
        ),
      ],
      child: MaterialApp(
        home: ContentViewPage(
          resourceId: resourceId,
          contentType: contentType,
          audioSeekService: audioSeekService,
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  group('ContentViewPage', () {
    testWidgets('shows loading indicator initially', (tester) async {
      final repository = FakeContentRepository();
      repository.delay = const Duration(seconds: 1);
      repository.nextResult = Result.success(_sampleAudioContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Let the delayed repository future complete to avoid pending timers.
      repository.delay = Duration.zero;
      await tester.pumpAndSettle();
    });

    testWidgets('renders audio title and SRT list on success', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_sampleAudioContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      expect(find.text('音频字幕'), findsOneWidget);
      expect(find.byType(SrtListView), findsOneWidget);
      expect(find.text('Hello world'), findsOneWidget);
    });

    testWidgets('renders PDF title and PDF text view on success', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_samplePdfContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.pdf,
        repository: repository,
      );
      await tester.pumpAndSettle();

      expect(find.text('PDF 文本'), findsOneWidget);
      expect(find.byType(PdfTextView), findsOneWidget);
      expect(find.text('第 1 页'), findsOneWidget);
    });

    testWidgets('shows network error with retry button', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextError = const NetworkException();

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      expect(find.text(const NetworkException().message), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('shows processing error with refresh label', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextError = const TaskNotCompletedException();

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      expect(find.text(const TaskNotCompletedException().message), findsOneWidget);
      expect(find.text('刷新'), findsOneWidget);
    });

    testWidgets('retry button reloads content', (WidgetTester tester) async {
      final repository = FakeContentRepository();
      repository.nextError = const NetworkException();

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      repository.nextError = null;
      repository.nextResult = Result.success(_sampleAudioContent());
      await tester.tap(find.text('重试'));
      await tester.pumpAndSettle();

      expect(find.byType(SrtListView), findsOneWidget);
      expect(repository.callCount, 2);
    });

    testWidgets('search highlights matches and shows count', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_sampleAudioContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('content_search_field')),
        'world',
      );
      await tester.pumpAndSettle(const Duration(milliseconds: 350));

      expect(find.byKey(const Key('content_search_count')), findsOneWidget);
      expect(find.text('1 / 1'), findsOneWidget);
    });

    testWidgets('tapping timestamp seeks audio', (WidgetTester tester) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_sampleAudioContent());
      final seekService = _FakeAudioSeekService();

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
        audioSeekService: seekService,
      );
      await tester.pumpAndSettle();

      await tester.tap(find.textContaining('00:00:01,000'));
      await tester.pump();

      expect(seekService.lastPosition, const Duration(seconds: 1));
    });

    testWidgets('text mode toggle switches between cleaned and original', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_sampleAudioContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.audio,
        repository: repository,
      );
      await tester.pumpAndSettle();

      expect(find.text('查看原文'), findsOneWidget);
      expect(find.text('Hello world'), findsOneWidget);

      await tester.tap(find.text('查看原文'));
      await tester.pumpAndSettle();

      expect(find.text('查看清洗文本'), findsOneWidget);
      expect(find.text('Original transcript'), findsOneWidget);
    });

    testWidgets('PDF page expands and collapses on tap', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_samplePdfContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.pdf,
        repository: repository,
      );
      await tester.pumpAndSettle();

      // First page is expanded by default.
      expect(find.text('First page'), findsOneWidget);

      await tester.tap(find.text('第 1 页'));
      await tester.pumpAndSettle();

      expect(find.text('First page'), findsNothing);

      await tester.tap(find.text('第 1 页'));
      await tester.pumpAndSettle();

      expect(find.text('First page'), findsOneWidget);
    });

    testWidgets('PDF search navigation expands page containing match', (
      WidgetTester tester,
    ) async {
      final repository = FakeContentRepository();
      repository.nextResult = Result.success(_samplePdfContent());

      await _pumpContentViewPage(
        tester,
        resourceId: 't1',
        contentType: ContentType.pdf,
        repository: repository,
      );
      await tester.pumpAndSettle();

      // Second page is collapsed by default.
      expect(find.text('Second page'), findsNothing);

      await tester.enterText(
        find.byKey(const Key('content_search_field')),
        'page',
      );
      await tester.pumpAndSettle(const Duration(milliseconds: 350));

      expect(find.text('1 / 2'), findsOneWidget);

      await tester.tap(find.byKey(const Key('content_search_next')));
      await tester.pumpAndSettle();

      expect(find.text('2 / 2'), findsOneWidget);
      expect(find.text('Second page'), findsOneWidget);
    });
  });
}
