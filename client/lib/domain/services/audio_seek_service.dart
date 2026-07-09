import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Service abstraction for seeking an audio player to a specific position.
///
/// Concrete implementations can wrap [just_audio] or any other player.
abstract class AudioSeekService {
  /// Seeks the audio player to [position].
  void seek(Duration position);
}

class _NoOpAudioSeekService implements AudioSeekService {
  @override
  void seek(Duration position) {}
}

/// Global provider for audio seeking.
///
/// Override this with a concrete implementation when an audio player is
/// available.
final audioSeekServiceProvider = Provider<AudioSeekService>(
  (ref) => _NoOpAudioSeekService(),
);
