import 'dart:typed_data';

/// Cross-platform representation of a file selected by the user.
///
/// Mobile/desktop clients populate [path] while Web clients populate [bytes].
class PickedFile {
  const PickedFile({
    this.path,
    this.bytes,
    required this.name,
    required this.size,
    this.extension,
  });

  final String? path;
  final Uint8List? bytes;
  final String name;
  final int size;
  final String? extension;
}
