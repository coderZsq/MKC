import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/constants.dart';
import '../../data/datasources/remote/content_remote_datasource.dart';
import '../../data/repositories/content_repository_impl.dart';
import '../../domain/entities/content.dart';
import '../../domain/entities/content_type.dart';
import '../../domain/repositories/content_repository.dart';
import '../../shared/errors/app_exception.dart';
import '../providers/task_center_provider.dart';

/// A single search match inside a content item.
class TextMatch {
  const TextMatch({
    required this.itemIndex,
    required this.startOffset,
    required this.endOffset,
  });

  /// Index of the content item containing the match (SRT segment or PDF page).
  final int itemIndex;

  /// Start offset of the match within the item text.
  final int startOffset;

  /// End offset (exclusive) of the match within the item text.
  final int endOffset;
}

/// UI state for the content view page.
class ContentViewState {
  const ContentViewState({
    this.isLoading = false,
    this.error,
    this.content,
    this.keyword = '',
    this.matches = const [],
    this.currentMatchIndex = -1,
    this.showCleanedText = true,
    this.expandedPageNumbers = const {},
  });

  final bool isLoading;
  final AppException? error;
  final Content? content;
  final String keyword;
  final List<TextMatch> matches;
  final int currentMatchIndex;
  final bool showCleanedText;
  final Set<int> expandedPageNumbers;

  ContentViewState copyWith({
    bool? isLoading,
    AppException? error,
    Content? content,
    String? keyword,
    List<TextMatch>? matches,
    int? currentMatchIndex,
    bool? showCleanedText,
    Set<int>? expandedPageNumbers,
  }) {
    return ContentViewState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      content: content ?? this.content,
      keyword: keyword ?? this.keyword,
      matches: matches ?? this.matches,
      currentMatchIndex: currentMatchIndex ?? this.currentMatchIndex,
      showCleanedText: showCleanedText ?? this.showCleanedText,
      expandedPageNumbers: expandedPageNumbers ?? this.expandedPageNumbers,
    );
  }
}

/// Manages loading, search, navigation and display options for content view.
class ContentViewNotifier extends StateNotifier<ContentViewState> {
  ContentViewNotifier({
    required ContentRepository repository,
    required String resourceId,
    required ContentType contentType,
    int? initialPage,
  })  : _repository = repository,
        _resourceId = resourceId,
        _contentType = contentType,
        _initialPage = initialPage,
        super(const ContentViewState());

  final ContentRepository _repository;
  final String _resourceId;
  final ContentType _contentType;
  final int? _initialPage;
  Timer? _debounceTimer;

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repository.getContent(_resourceId, _contentType);
    state = result.when(
      success: (content) {
        final expanded = <int>{};
        if (content is PdfContent && content.pages.isNotEmpty) {
          final pageNumbers = content.pages.map((page) => page.pageNumber);
          final targetPage = _initialPage;
          expanded.add(
            targetPage != null && pageNumbers.contains(targetPage)
                ? targetPage
                : content.pages.first.pageNumber,
          );
        }
        return state.copyWith(
          isLoading: false,
          content: content,
          keyword: '',
          matches: const [],
          currentMatchIndex: -1,
          expandedPageNumbers: expanded,
        );
      },
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  Future<void> retry() => load();

  void onSearchChanged(String keyword) {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(
      const Duration(milliseconds: ContentViewConfig.searchDebounceMs),
      () {
        if (mounted) _applySearch(keyword.trim());
      },
    );
  }

  void _applySearch(String keyword) {
    final matches = _buildMatches(keyword);
    final currentIndex = matches.isEmpty ? -1 : 0;
    state = state.copyWith(
      keyword: keyword,
      matches: matches,
      currentMatchIndex: currentIndex,
      expandedPageNumbers: _expandedForMatch(matches, currentIndex),
    );
  }

  Set<int> _expandedForMatch(List<TextMatch> matches, int currentIndex) {
    final content = state.content;
    if (content is! PdfContent) return state.expandedPageNumbers;
    if (currentIndex < 0 || currentIndex >= matches.length) {
      return state.expandedPageNumbers;
    }
    final pageIndex = matches[currentIndex].itemIndex;
    if (pageIndex < 0 || pageIndex >= content.pages.length) {
      return state.expandedPageNumbers;
    }
    return {...state.expandedPageNumbers, content.pages[pageIndex].pageNumber};
  }

  List<TextMatch> _buildMatches(String keyword) {
    if (keyword.isEmpty) return const [];
    final content = state.content;
    if (content == null) return const [];

    final lowerKeyword = keyword.toLowerCase();
    final matches = <TextMatch>[];

    switch (content) {
      case AudioContent(:final segments):
        for (var i = 0; i < segments.length; i++) {
          final text =
              segments[i].displayText(showCleaned: state.showCleanedText);
          matches.addAll(_findMatchesInText(i, text, lowerKeyword));
          if (matches.length >= ContentViewConfig.maxHighlightMatches) break;
        }
      case PdfContent(:final pages):
        for (var i = 0; i < pages.length; i++) {
          final text = pages[i].text;
          matches.addAll(_findMatchesInText(i, text, lowerKeyword));
          if (matches.length >= ContentViewConfig.maxHighlightMatches) break;
        }
    }

    return matches.length > ContentViewConfig.maxHighlightMatches
        ? matches.sublist(0, ContentViewConfig.maxHighlightMatches)
        : matches;
  }

  List<TextMatch> _findMatchesInText(
    int itemIndex,
    String text,
    String lowerKeyword,
  ) {
    final pattern = RegExp(
      RegExp.escape(lowerKeyword),
      caseSensitive: false,
    );
    return pattern
        .allMatches(text)
        .map(
          (match) => TextMatch(
            itemIndex: itemIndex,
            startOffset: match.start,
            endOffset: match.end,
          ),
        )
        .toList();
  }

  void jumpToNextMatch() {
    if (state.matches.isEmpty) return;
    final next = (state.currentMatchIndex + 1) % state.matches.length;
    state = state.copyWith(
      currentMatchIndex: next,
      expandedPageNumbers: _expandedForMatch(state.matches, next),
    );
  }

  void jumpToPreviousMatch() {
    if (state.matches.isEmpty) return;
    final previous = (state.currentMatchIndex - 1 + state.matches.length) %
        state.matches.length;
    state = state.copyWith(
      currentMatchIndex: previous,
      expandedPageNumbers: _expandedForMatch(state.matches, previous),
    );
  }

  void toggleTextMode() {
    final newValue = !state.showCleanedText;
    state = state.copyWith(showCleanedText: newValue);
    if (state.keyword.isNotEmpty) {
      _applySearch(state.keyword);
    }
  }

  void togglePageExpanded(int pageNumber) {
    final updated = Set<int>.of(state.expandedPageNumbers);
    if (updated.contains(pageNumber)) {
      updated.remove(pageNumber);
    } else {
      updated.add(pageNumber);
    }
    state = state.copyWith(expandedPageNumbers: updated);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}

/// Arguments used to identify a content view page instance.
class ContentViewRouteArgs {
  const ContentViewRouteArgs({
    required this.resourceId,
    required this.contentType,
    this.initialPage,
  });

  final String resourceId;
  final ContentType contentType;
  final int? initialPage;

  @override
  bool operator ==(Object other) =>
      other is ContentViewRouteArgs &&
      other.resourceId == resourceId &&
      other.contentType == contentType &&
      other.initialPage == initialPage;

  @override
  int get hashCode => Object.hash(resourceId, contentType, initialPage);
}

final contentRemoteDataSourceProvider =
    Provider<ContentRemoteDataSource>((ref) {
  return ContentRemoteDataSource();
});

final contentRepositoryProvider = Provider<ContentRepository>((ref) {
  return ContentRepositoryImpl(
    taskApi: ref.watch(taskApiProvider),
    remoteDataSource: ref.watch(contentRemoteDataSourceProvider),
  );
});

final contentViewNotifierProvider = StateNotifierProvider.autoDispose
    .family<ContentViewNotifier, ContentViewState, ContentViewRouteArgs>(
  (ref, args) => ContentViewNotifier(
    repository: ref.watch(contentRepositoryProvider),
    resourceId: args.resourceId,
    contentType: args.contentType,
    initialPage: args.initialPage,
  ),
);
