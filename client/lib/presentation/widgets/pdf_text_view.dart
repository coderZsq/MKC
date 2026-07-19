import 'package:flutter/material.dart';

import '../../core/responsive/breakpoints.dart';
import '../../domain/entities/parsed_page.dart';
import '../providers/content_view_provider.dart';
import 'claude_layout.dart';
import 'highlight_text.dart';

/// Collapsible page-based view for parsed PDF text.
class PdfTextView extends StatefulWidget {
  const PdfTextView({
    required this.pages,
    this.initialPage,
    required this.expandedPageNumbers,
    required this.matches,
    required this.currentMatchIndex,
    required this.keyword,
    required this.onToggleExpanded,
    super.key,
  });

  final List<ParsedPage> pages;
  final int? initialPage;
  final Set<int> expandedPageNumbers;
  final List<TextMatch> matches;
  final int currentMatchIndex;
  final String keyword;
  final ValueChanged<int> onToggleExpanded;

  @override
  State<PdfTextView> createState() => _PdfTextViewState();
}

class _PdfTextViewState extends State<PdfTextView> {
  final _scrollController = ScrollController();
  final _itemKeys = <int, GlobalKey>{};
  int? _lastScrolledInitialPage;

  @override
  void initState() {
    super.initState();
    _scrollToInitialPage();
  }

  @override
  void didUpdateWidget(covariant PdfTextView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialPage != widget.initialPage ||
        oldWidget.pages != widget.pages) {
      _scrollToInitialPage();
    }
    if (oldWidget.currentMatchIndex != widget.currentMatchIndex) {
      _scrollToCurrentMatch();
    }
  }

  void _scrollToInitialPage() {
    final pageNumber = widget.initialPage;
    if (pageNumber == null || _lastScrolledInitialPage == pageNumber) return;
    final index =
        widget.pages.indexWhere((page) => page.pageNumber == pageNumber);
    if (index < 0) return;
    _lastScrolledInitialPage = pageNumber;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final key = _itemKeys[index];
      if (key?.currentContext != null) {
        Scrollable.ensureVisible(
          key!.currentContext!,
          duration: const Duration(milliseconds: 220),
          alignment: 0.08,
        );
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToCurrentMatch() {
    final index = widget.currentMatchIndex;
    if (index < 0 || index >= widget.matches.length) return;
    final match = widget.matches[index];
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final key = _itemKeys[match.itemIndex];
      if (key?.currentContext != null) {
        Scrollable.ensureVisible(
          key!.currentContext!,
          duration: const Duration(milliseconds: 200),
          alignment: 0.2,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      padding: EdgeInsets.fromLTRB(
        context.isCompactWidth ? 8 : 12,
        4,
        context.isCompactWidth ? 8 : 12,
        28,
      ),
      itemCount: widget.pages.length,
      itemBuilder: (context, index) {
        final page = widget.pages[index];
        return _PageTile(
          key: _itemKey(index),
          page: page,
          isExpanded: widget.expandedPageNumbers.contains(page.pageNumber),
          keyword: widget.keyword,
          match: _matchForPage(index),
          onToggle: () => widget.onToggleExpanded(page.pageNumber),
        );
      },
    );
  }

  GlobalKey _itemKey(int index) {
    return _itemKeys.putIfAbsent(index, GlobalKey.new);
  }

  TextMatch? _matchForPage(int pageIndex) {
    final index = widget.currentMatchIndex;
    if (index < 0 || index >= widget.matches.length) return null;
    final match = widget.matches[index];
    return match.itemIndex == pageIndex ? match : null;
  }
}

class _PageTile extends StatelessWidget {
  const _PageTile({
    required this.page,
    required this.isExpanded,
    required this.keyword,
    required this.match,
    required this.onToggle,
    super.key,
  });

  final ParsedPage page;
  final bool isExpanded;
  final String keyword;
  final TextMatch? match;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: ClaudePanel(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            ListTile(
              title: Text('第 ${page.pageNumber} 页'),
              trailing: Icon(
                isExpanded ? Icons.expand_less : Icons.expand_more,
              ),
              onTap: onToggle,
            ),
            if (isExpanded)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: HighlightText(
                  text: page.text,
                  keyword: keyword,
                  highlightStart: match?.startOffset ?? -1,
                  highlightEnd: match?.endOffset ?? -1,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
