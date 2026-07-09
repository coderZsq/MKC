import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/services/audio_seek_service.dart';

void main() {
  group('AudioSeekService', () {
    test('default provider returns no-op implementation', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final service = container.read(audioSeekServiceProvider);

      expect(service, isA<AudioSeekService>());
      expect(() => service.seek(Duration.zero), returnsNormally);
    });
  });
}
