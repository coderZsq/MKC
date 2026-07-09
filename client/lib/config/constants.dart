/// Application-wide constants.
abstract final class Constants {
  static const String appName = 'MKC';
  static const String appSubtitle = 'Multimedia Knowledge Companion';
  static const Duration splashDuration = Duration(seconds: 2);
  static const Duration defaultTimeout = Duration(seconds: 30);
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;
}

/// Content view page configuration.
abstract final class ContentViewConfig {
  static const Duration segmentFoldDuration = Duration(seconds: 30);
  static const int searchDebounceMs = 300;
  static const int maxHighlightMatches = 100;
}
