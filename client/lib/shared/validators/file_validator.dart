import '../errors/app_exception.dart';
import '../../core/platform/platform_capabilities.dart';

/// Allowed upload extensions for Sprint 1.
const Set<String> allowedExtensions = {
  'mp3',
  'wav',
  'mp4',
  'webm',
  'pdf',
  'txt',
  'doc',
  'docx',
};

/// Maximum upload size for mobile/desktop clients.
const int maxSizeBytes = PlatformUploadLimits.native;

/// Maximum upload size for Web clients to avoid browser memory issues.
const int webMaxSizeBytes = PlatformUploadLimits.web;

/// Returns the MIME type for a given extension, or `null` if unknown.
String? mimeFromExtension(String? extension) {
  return switch (extension?.toLowerCase()) {
    'mp3' => 'audio/mpeg',
    'wav' => 'audio/wav',
    'mp4' => 'video/mp4',
    'webm' => 'video/webm',
    'pdf' => 'application/pdf',
    'txt' => 'text/plain',
    'doc' => 'application/msword',
    'docx' =>
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    _ => null,
  };
}

/// Validates a selected file before upload.
///
/// Returns an [AppException] when the file is too large or has an unsupported
/// extension; otherwise returns `null`.
AppException? validatePickedFile({
  required int size,
  required String? extension,
  required bool isWeb,
}) {
  final maxSize = isWeb ? webMaxSizeBytes : maxSizeBytes;
  if (size > maxSize) {
    return const FileSizeLimitException();
  }
  if (!allowedExtensions.contains(extension?.toLowerCase())) {
    return const UnsupportedFileTypeException();
  }
  return null;
}
