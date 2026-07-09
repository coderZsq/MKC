/// A single subtitle segment parsed from an SRT file.
class SubtitleSegment {
  const SubtitleSegment({
    required this.index,
    required this.start,
    required this.end,
    required this.text,
    this.originalText,
  });

  final int index;
  final Duration start;
  final Duration end;

  /// Cleaned text (from SRT). This is the default text shown to the user.
  final String text;

  /// Optional original transcript text before cleaning.
  final String? originalText;

  /// Returns the display text for the given [showCleaned] mode.
  String displayText({required bool showCleaned}) {
    if (showCleaned) return text;
    return originalText ?? text;
  }

  SubtitleSegment copyWith({
    int? index,
    Duration? start,
    Duration? end,
    String? text,
    String? originalText,
  }) {
    return SubtitleSegment(
      index: index ?? this.index,
      start: start ?? this.start,
      end: end ?? this.end,
      text: text ?? this.text,
      originalText: originalText ?? this.originalText,
    );
  }
}
