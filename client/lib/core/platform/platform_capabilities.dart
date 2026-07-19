import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Cross-platform capability flags used by UI and providers.
class PlatformCapabilities {
  const PlatformCapabilities({
    required this.supportsFilePicker,
    required this.supportsSse,
    required this.isWeb,
    required this.isMobile,
    required this.isDesktop,
    required this.uploadsRequireInMemoryBytes,
    required this.maxUploadBytes,
  });

  factory PlatformCapabilities.current() {
    final platform = defaultTargetPlatform;
    final isMobile = !kIsWeb &&
        (platform == TargetPlatform.android || platform == TargetPlatform.iOS);
    final isDesktop = !kIsWeb &&
        (platform == TargetPlatform.macOS ||
            platform == TargetPlatform.windows ||
            platform == TargetPlatform.linux);
    return PlatformCapabilities(
      supportsFilePicker: true,
      supportsSse: true,
      isWeb: kIsWeb,
      isMobile: isMobile,
      isDesktop: isDesktop,
      uploadsRequireInMemoryBytes: kIsWeb,
      maxUploadBytes:
          kIsWeb ? PlatformUploadLimits.web : PlatformUploadLimits.native,
    );
  }

  final bool supportsFilePicker;
  final bool supportsSse;
  final bool isWeb;
  final bool isMobile;
  final bool isDesktop;
  final bool uploadsRequireInMemoryBytes;
  final int maxUploadBytes;
}

/// Shared upload limits for platform-aware validation and documentation.
abstract final class PlatformUploadLimits {
  static const int native = 500 * 1024 * 1024;
  static const int web = 100 * 1024 * 1024;
}

final platformCapabilitiesProvider = Provider<PlatformCapabilities>((ref) {
  return PlatformCapabilities.current();
});
