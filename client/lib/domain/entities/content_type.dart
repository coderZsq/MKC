/// Type of content displayed on the content view page.
enum ContentType {
  audio,
  pdf;

  /// Parses a query-parameter value into [ContentType].
  ///
  /// Returns [pdf] for any unrecognized value as a safe default.
  static ContentType fromParam(String? value) {
    return switch (value) {
      'audio' => ContentType.audio,
      _ => ContentType.pdf,
    };
  }

  String get paramValue {
    return switch (this) {
      ContentType.audio => 'audio',
      ContentType.pdf => 'pdf',
    };
  }
}
