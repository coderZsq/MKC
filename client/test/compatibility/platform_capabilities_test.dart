import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/core/platform/platform_capabilities.dart';
import 'package:mkc_client/core/responsive/breakpoints.dart';

void main() {
  group('PlatformCapabilities', () {
    test('exposes explicit upload limits', () {
      const caps = PlatformCapabilities(
        supportsFilePicker: true,
        supportsSse: true,
        isWeb: true,
        isMobile: false,
        isDesktop: false,
        uploadsRequireInMemoryBytes: true,
        maxUploadBytes: PlatformUploadLimits.web,
      );

      expect(caps.supportsFilePicker, isTrue);
      expect(caps.supportsSse, isTrue);
      expect(caps.uploadsRequireInMemoryBytes, isTrue);
      expect(caps.maxUploadBytes, 100 * 1024 * 1024);
    });
  });

  group('responsiveSizeClassForWidth', () {
    test('maps compact, medium, and expanded widths', () {
      expect(
        responsiveSizeClassForWidth(390),
        ResponsiveSizeClass.compact,
      );
      expect(
        responsiveSizeClassForWidth(834),
        ResponsiveSizeClass.medium,
      );
      expect(
        responsiveSizeClassForWidth(1440),
        ResponsiveSizeClass.expanded,
      );
    });
  });
}
