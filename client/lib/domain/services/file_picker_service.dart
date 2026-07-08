import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';

import '../entities/picked_file.dart';

/// Abstraction over the system file picker so the upload layer can be tested.
abstract interface class FilePickerService {
  Future<PickedFile?> pickSingleFile();
}

/// Default implementation backed by `file_picker`.
class FilePickerServiceImpl implements FilePickerService {
  @override
  Future<PickedFile?> pickSingleFile() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      withData: kIsWeb,
      withReadStream: !kIsWeb,
    );

    if (result == null || result.files.isEmpty) {
      return null;
    }

    final file = result.files.first;
    return PickedFile(
      path: kIsWeb ? null : file.path,
      bytes: kIsWeb ? file.bytes : null,
      name: file.name,
      size: file.size,
      extension: file.extension?.toLowerCase(),
    );
  }
}
