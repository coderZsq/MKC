import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/content.dart';
import '../../domain/entities/content_type.dart';
import '../../domain/services/audio_seek_service.dart';
import '../../shared/errors/app_exception.dart';
import '../providers/content_view_provider.dart';
import '../widgets/pdf_text_view.dart';
import '../widgets/srt_list_view.dart';
import '../widgets/text_search_bar.dart';

/// Page displaying task result content (SRT subtitles or parsed PDF text).
class ContentViewPage extends ConsumerStatefulWidget {
  const ContentViewPage({
    required this.resourceId,
    required this.contentType,
    this.initialPage,
    this.initialTimestamp,
    this.audioSeekService,
    super.key,
  });

  final String resourceId;
  final ContentType contentType;
  final int? initialPage;
  final Duration? initialTimestamp;
  final AudioSeekService? audioSeekService;

  @override
  ConsumerState<ContentViewPage> createState() => _ContentViewPageState();
}

class _ContentViewPageState extends ConsumerState<ContentViewPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(_provider.notifier).load();
    });
  }

  AutoDisposeStateNotifierProvider<ContentViewNotifier, ContentViewState>
      get _provider => contentViewNotifierProvider(_args);

  ContentViewRouteArgs get _args => ContentViewRouteArgs(
        resourceId: widget.resourceId,
        contentType: widget.contentType,
        initialPage: widget.initialPage,
      );

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(_provider);
    final audioSeekService = (widget.audioSeekService ??
        ref.watch(audioSeekServiceProvider)) as AudioSeekService;

    return Scaffold(
      appBar: AppBar(
        title: Text(_pageTitle(state.content)),
        actions: [
          if (state.content is AudioContent)
            _TextModeToggle(
              showCleanedText: state.showCleanedText,
              onToggle: () => ref.read(_provider.notifier).toggleTextMode(),
            ),
        ],
      ),
      body: Column(
        children: [
          TextSearchBar(
            keyword: state.keyword,
            matchCount: state.matches.length,
            currentIndex: state.currentMatchIndex,
            onChanged: (value) =>
                ref.read(_provider.notifier).onSearchChanged(value),
            onPrevious: () =>
                ref.read(_provider.notifier).jumpToPreviousMatch(),
            onNext: () => ref.read(_provider.notifier).jumpToNextMatch(),
          ),
          Expanded(child: _buildBody(context, state, audioSeekService)),
        ],
      ),
    );
  }

  String _pageTitle(Content? content) {
    return switch (content?.type) {
      ContentType.audio => '音频字幕',
      ContentType.pdf => 'PDF 文本',
      _ => '内容查看',
    };
  }

  Widget _buildBody(BuildContext context, ContentViewState state,
      AudioSeekService audioSeekService) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final error = state.error;
    if (error != null) {
      return _ErrorView(
          error: error, onRetry: () => ref.read(_provider.notifier).retry());
    }

    final content = state.content;
    if (content == null) {
      return const _CompactState(
        message: '暂无内容',
        icon: Icons.article_outlined,
      );
    }

    return switch (content) {
      AudioContent(:final segments) => SrtListView(
          segments: segments,
          initialTimestamp: widget.initialTimestamp,
          matches: state.matches,
          currentMatchIndex: state.currentMatchIndex,
          showCleanedText: state.showCleanedText,
          keyword: state.keyword,
          onTimestampTap: (segment) => audioSeekService.seek(segment.start),
        ),
      PdfContent(:final pages) => PdfTextView(
          pages: pages,
          initialPage: widget.initialPage,
          expandedPageNumbers: state.expandedPageNumbers,
          matches: state.matches,
          currentMatchIndex: state.currentMatchIndex,
          keyword: state.keyword,
          onToggleExpanded: (pageNumber) =>
              ref.read(_provider.notifier).togglePageExpanded(pageNumber),
        ),
    };
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.error, required this.onRetry});

  final AppException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final isNotCompleted = error is TaskNotCompletedException;

    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 360),
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(8),
          border:
              Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isNotCompleted ? Icons.hourglass_empty : Icons.wifi_off_outlined,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 12),
            Text(error.message),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: onRetry,
              child: Text(isNotCompleted ? '刷新' : '重试'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CompactState extends StatelessWidget {
  const _CompactState({required this.message, required this.icon});

  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(8),
          border:
              Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class _TextModeToggle extends StatelessWidget {
  const _TextModeToggle({
    required this.showCleanedText,
    required this.onToggle,
  });

  final bool showCleanedText;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onToggle,
      child: Text(showCleanedText ? '查看原文' : '查看清洗文本'),
    );
  }
}
