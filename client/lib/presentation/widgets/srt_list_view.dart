import 'package:flutter/material.dart';

import '../../config/constants.dart';
import '../../domain/entities/subtitle_segment.dart';
import '../providers/content_view_provider.dart';
import 'claude_layout.dart';
import 'highlight_text.dart';

/// Formats a duration as an SRT timecode `HH:mm:ss,fff`.
String formatSrtTimecode(Duration duration) {
  final hours = duration.inHours.toString().padLeft(2, '0');
  final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
  final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
  final millis =
      duration.inMilliseconds.remainder(1000).toString().padLeft(3, '0');
  return '$hours:$minutes:$seconds,$millis';
}

/// A subtitle segment together with its original index in the full list.
class _IndexedSegment {
  const _IndexedSegment(this.globalIndex, this.segment);

  final int globalIndex;
  final SubtitleSegment segment;
}

/// A group of subtitle segments that fall within the same fold window.
class _SegmentBucket {
  _SegmentBucket({required this.start, required this.end});

  final Duration start;
  final Duration end;
  final List<_IndexedSegment> segments = [];
}

/// List view for SRT subtitle segments, folded into fixed-duration buckets.
class SrtListView extends StatefulWidget {
  const SrtListView({
    required this.segments,
    this.initialTimestamp,
    required this.matches,
    required this.currentMatchIndex,
    required this.showCleanedText,
    required this.keyword,
    this.onTimestampTap,
    super.key,
  });

  final List<SubtitleSegment> segments;
  final Duration? initialTimestamp;
  final List<TextMatch> matches;
  final int currentMatchIndex;
  final bool showCleanedText;
  final String keyword;
  final ValueChanged<SubtitleSegment>? onTimestampTap;

  @override
  State<SrtListView> createState() => _SrtListViewState();
}

class _SrtListViewState extends State<SrtListView> {
  final _scrollController = ScrollController();
  final _bucketKeys = <int, GlobalKey>{};
  final _segmentKeys = <int, GlobalKey>{};
  final _expandedBucketIndices = <int>{0};
  Duration? _lastScrolledInitialTimestamp;

  @override
  void initState() {
    super.initState();
    if (widget.segments.isEmpty) {
      _expandedBucketIndices.clear();
    }
    _ensureBucketExpandedForInitialTimestamp();
    _scrollToInitialTimestamp();
  }

  @override
  void didUpdateWidget(covariant SrtListView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialTimestamp != widget.initialTimestamp ||
        oldWidget.segments != widget.segments) {
      _ensureBucketExpandedForInitialTimestamp();
      _scrollToInitialTimestamp();
    }
    if (oldWidget.currentMatchIndex != widget.currentMatchIndex) {
      _ensureBucketExpandedForCurrentMatch();
      _scrollToCurrentMatch();
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  List<_SegmentBucket> _buildBuckets() {
    final buckets = <_SegmentBucket>[];
    final foldSeconds = ContentViewConfig.segmentFoldDuration.inSeconds;
    for (var i = 0; i < widget.segments.length; i++) {
      final segment = widget.segments[i];
      final bucketStart = Duration(
        seconds: segment.start.inSeconds ~/ foldSeconds * foldSeconds,
      );
      final bucketEnd = Duration(seconds: bucketStart.inSeconds + foldSeconds);
      if (buckets.isEmpty || buckets.last.start != bucketStart) {
        buckets.add(
          _SegmentBucket(start: bucketStart, end: bucketEnd),
        );
      }
      buckets.last.segments.add(_IndexedSegment(i, segment));
    }
    return buckets;
  }

  int? _bucketIndexForSegment(int segmentIndex) {
    final buckets = _buildBuckets();
    for (var i = 0; i < buckets.length; i++) {
      final bucket = buckets[i];
      for (final indexed in bucket.segments) {
        if (indexed.globalIndex == segmentIndex) return i;
      }
    }
    return null;
  }

  int? _segmentIndexForTimestamp(Duration? timestamp) {
    if (timestamp == null) return null;
    for (var i = 0; i < widget.segments.length; i++) {
      final segment = widget.segments[i];
      if (timestamp >= segment.start && timestamp <= segment.end) {
        return i;
      }
    }
    for (var i = 0; i < widget.segments.length; i++) {
      if (timestamp <= widget.segments[i].end) {
        return i;
      }
    }
    if (widget.segments.isNotEmpty) {
      return widget.segments.length - 1;
    }
    return null;
  }

  void _ensureBucketExpandedForInitialTimestamp() {
    final segmentIndex = _segmentIndexForTimestamp(widget.initialTimestamp);
    if (segmentIndex == null) return;
    final bucketIndex = _bucketIndexForSegment(segmentIndex);
    if (bucketIndex == null) return;
    _expandedBucketIndices.add(bucketIndex);
  }

  void _scrollToInitialTimestamp() {
    final timestamp = widget.initialTimestamp;
    if (timestamp == null || _lastScrolledInitialTimestamp == timestamp) return;
    final segmentIndex = _segmentIndexForTimestamp(timestamp);
    if (segmentIndex == null) return;
    _lastScrolledInitialTimestamp = timestamp;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final key = _segmentKeys[segmentIndex];
      if (key?.currentContext != null) {
        Scrollable.ensureVisible(
          key!.currentContext!,
          duration: const Duration(milliseconds: 220),
          alignment: 0.16,
        );
      }
    });
  }

  void _ensureBucketExpandedForCurrentMatch() {
    final index = widget.currentMatchIndex;
    if (index < 0 || index >= widget.matches.length) return;
    final segmentIndex = widget.matches[index].itemIndex;
    final bucketIndex = _bucketIndexForSegment(segmentIndex);
    if (bucketIndex == null) return;
    if (!_expandedBucketIndices.contains(bucketIndex)) {
      setState(() => _expandedBucketIndices.add(bucketIndex));
    }
  }

  void _scrollToCurrentMatch() {
    final index = widget.currentMatchIndex;
    if (index < 0 || index >= widget.matches.length) return;
    final match = widget.matches[index];
    final key = _segmentKeys[match.itemIndex];
    if (key?.currentContext == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
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
    final buckets = _buildBuckets();
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 28),
      itemCount: buckets.length,
      itemBuilder: (context, index) {
        final bucket = buckets[index];
        return _BucketTile(
          key: _bucketKey(index),
          bucket: bucket,
          isExpanded: _expandedBucketIndices.contains(index),
          showCleanedText: widget.showCleanedText,
          keyword: widget.keyword,
          matches: widget.matches,
          currentMatchIndex: widget.currentMatchIndex,
          onTimestampTap: widget.onTimestampTap,
          onToggle: () => setState(() {
            if (_expandedBucketIndices.contains(index)) {
              _expandedBucketIndices.remove(index);
            } else {
              _expandedBucketIndices.add(index);
            }
          }),
          segmentKeyBuilder: _segmentKey,
        );
      },
    );
  }

  GlobalKey _bucketKey(int index) {
    return _bucketKeys.putIfAbsent(index, GlobalKey.new);
  }

  GlobalKey _segmentKey(int index) {
    return _segmentKeys.putIfAbsent(index, GlobalKey.new);
  }
}

class _BucketTile extends StatelessWidget {
  const _BucketTile({
    required this.bucket,
    required this.isExpanded,
    required this.showCleanedText,
    required this.keyword,
    required this.matches,
    required this.currentMatchIndex,
    required this.onTimestampTap,
    required this.onToggle,
    required this.segmentKeyBuilder,
    super.key,
  });

  final _SegmentBucket bucket;
  final bool isExpanded;
  final bool showCleanedText;
  final String keyword;
  final List<TextMatch> matches;
  final int currentMatchIndex;
  final ValueChanged<SubtitleSegment>? onTimestampTap;
  final VoidCallback onToggle;
  final GlobalKey Function(int index) segmentKeyBuilder;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: ClaudePanel(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            ListTile(
              title: Text(
                '${formatSrtTimecode(bucket.start)} - ${formatSrtTimecode(bucket.end)}',
              ),
              trailing: Icon(
                isExpanded ? Icons.expand_less : Icons.expand_more,
              ),
              onTap: onToggle,
            ),
            if (isExpanded)
              ...bucket.segments.map((indexed) {
                return _SegmentTile(
                  key: segmentKeyBuilder(indexed.globalIndex),
                  segment: indexed.segment,
                  showCleanedText: showCleanedText,
                  keyword: keyword,
                  highlightStart:
                      _matchForSegment(indexed.globalIndex)?.startOffset ?? -1,
                  highlightEnd:
                      _matchForSegment(indexed.globalIndex)?.endOffset ?? -1,
                  onTimestampTap: onTimestampTap,
                );
              }),
          ],
        ),
      ),
    );
  }

  TextMatch? _matchForSegment(int segmentIndex) {
    final index = currentMatchIndex;
    if (index < 0 || index >= matches.length) return null;
    final match = matches[index];
    return match.itemIndex == segmentIndex ? match : null;
  }
}

class _SegmentTile extends StatelessWidget {
  const _SegmentTile({
    required this.segment,
    required this.showCleanedText,
    required this.keyword,
    required this.highlightStart,
    required this.highlightEnd,
    this.onTimestampTap,
    super.key,
  });

  final SubtitleSegment segment;
  final bool showCleanedText;
  final String keyword;
  final int highlightStart;
  final int highlightEnd;
  final ValueChanged<SubtitleSegment>? onTimestampTap;

  @override
  Widget build(BuildContext context) {
    final text = segment.displayText(showCleaned: showCleanedText);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap:
                onTimestampTap == null ? null : () => onTimestampTap!(segment),
            child: Text(
              '${formatSrtTimecode(segment.start)} --> ${formatSrtTimecode(segment.end)}',
              style: TextStyle(
                color: onTimestampTap == null
                    ? Theme.of(context).disabledColor
                    : Theme.of(context).colorScheme.primary,
                fontFamily: 'monospace',
              ),
            ),
          ),
          const SizedBox(height: 8),
          HighlightText(
            text: text,
            keyword: keyword,
            highlightStart: highlightStart,
            highlightEnd: highlightEnd,
          ),
        ],
      ),
    );
  }
}
