import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/validators/file_validator.dart';

void main() {
  group('validatePickedFile', () {
    test('returns null for supported extensions', () {
      for (final ext in ['mp3', 'wav', 'mp4', 'webm', 'pdf', 'txt', 'doc', 'docx']) {
        expect(
          validatePickedFile(size: 1024, extension: ext, isWeb: false),
          isNull,
          reason: '$ext should be allowed',
        );
      }
    });

    test('returns UnsupportedFileTypeException for unknown extension', () {
      final result = validatePickedFile(
        size: 1024,
        extension: 'exe',
        isWeb: false,
      );
      expect(result, isA<UnsupportedFileTypeException>());
    });

    test('returns FileSizeLimitException when mobile file exceeds 500MB', () {
      final result = validatePickedFile(
        size: 501 * 1024 * 1024,
        extension: 'mp3',
        isWeb: false,
      );
      expect(result, isA<FileSizeLimitException>());
    });

    test('returns FileSizeLimitException when Web file exceeds 100MB', () {
      final result = validatePickedFile(
        size: 101 * 1024 * 1024,
        extension: 'mp3',
        isWeb: true,
      );
      expect(result, isA<FileSizeLimitException>());
    });

    test('allows Web file within 100MB', () {
      final result = validatePickedFile(
        size: 100 * 1024 * 1024,
        extension: 'pdf',
        isWeb: true,
      );
      expect(result, isNull);
    });
  });

  group('mimeFromExtension', () {
    test('maps extensions to correct MIME types', () {
      expect(mimeFromExtension('mp3'), 'audio/mpeg');
      expect(mimeFromExtension('wav'), 'audio/wav');
      expect(mimeFromExtension('mp4'), 'video/mp4');
      expect(mimeFromExtension('webm'), 'video/webm');
      expect(mimeFromExtension('pdf'), 'application/pdf');
      expect(mimeFromExtension('txt'), 'text/plain');
      expect(mimeFromExtension('doc'), 'application/msword');
      expect(
        mimeFromExtension('docx'),
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
    });

    test('returns null for unknown extension', () {
      expect(mimeFromExtension('xyz'), isNull);
      expect(mimeFromExtension(null), isNull);
    });
  });
}
