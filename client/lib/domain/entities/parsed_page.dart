/// A text block extracted from a PDF page.
class ParsedBlock {
  const ParsedBlock({
    required this.text,
    this.x,
    this.y,
    this.width,
    this.height,
  });

  final String text;
  final double? x;
  final double? y;
  final double? width;
  final double? height;
}

/// A single page parsed from a PDF document.
class ParsedPage {
  const ParsedPage({
    required this.pageNumber,
    required this.text,
    this.blocks = const [],
  });

  final int pageNumber;
  final String text;
  final List<ParsedBlock> blocks;

  ParsedPage copyWith({
    int? pageNumber,
    String? text,
    List<ParsedBlock>? blocks,
  }) {
    return ParsedPage(
      pageNumber: pageNumber ?? this.pageNumber,
      text: text ?? this.text,
      blocks: blocks ?? this.blocks,
    );
  }
}
