import 'package:flutter/material.dart';

/// Renders [text] with a highlighted range.
class HighlightText extends StatelessWidget {
  const HighlightText({
    required this.text,
    this.keyword,
    this.highlightStart = -1,
    this.highlightEnd = -1,
    this.style,
    this.highlightColor,
    this.highlightTextColor,
    super.key,
  });

  final String text;
  final String? keyword;

  /// Inclusive start offset of the active highlight range.
  final int highlightStart;

  /// Exclusive end offset of the active highlight range.
  final int highlightEnd;

  final TextStyle? style;
  final Color? highlightColor;
  final Color? highlightTextColor;

  @override
  Widget build(BuildContext context) {
    final effectiveStyle = style ?? DefaultTextStyle.of(context).style;
    final spans = _buildSpans(context, effectiveStyle);
    return Text.rich(TextSpan(children: spans), style: effectiveStyle);
  }

  List<TextSpan> _buildSpans(BuildContext context, TextStyle baseStyle) {
    final keywordValue = keyword;
    if (keywordValue == null || keywordValue.isEmpty) {
      return [TextSpan(text: text, style: baseStyle)];
    }

    final lowerText = text.toLowerCase();
    final lowerKeyword = keywordValue.toLowerCase();
    final spans = <TextSpan>[];
    var start = 0;

    while (true) {
      final index = lowerText.indexOf(lowerKeyword, start);
      if (index == -1) break;

      if (index > start) {
        spans.add(TextSpan(text: text.substring(start, index), style: baseStyle));
      }

      final isActive = index == highlightStart &&
          index + keywordValue.length == highlightEnd;
      spans.add(
        TextSpan(
          text: text.substring(index, index + keywordValue.length),
          style: baseStyle.copyWith(
            backgroundColor: isActive
                ? (highlightColor ?? Theme.of(context).colorScheme.primary)
                : (highlightColor ?? Theme.of(context).colorScheme.primaryContainer),
            color: isActive
                ? (highlightTextColor ?? Theme.of(context).colorScheme.onPrimary)
                : null,
          ),
        ),
      );
      start = index + keywordValue.length;
    }

    if (start < text.length) {
      spans.add(TextSpan(text: text.substring(start), style: baseStyle));
    }

    return spans.isEmpty ? [TextSpan(text: text, style: baseStyle)] : spans;
  }
}
