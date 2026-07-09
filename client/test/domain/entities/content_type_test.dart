import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/content_type.dart';

void main() {
  group('ContentType', () {
    test('fromParam parses audio and defaults to pdf', () {
      expect(ContentType.fromParam('audio'), ContentType.audio);
      expect(ContentType.fromParam(null), ContentType.pdf);
      expect(ContentType.fromParam('unknown'), ContentType.pdf);
    });

    test('paramValue returns audio or pdf string', () {
      expect(ContentType.audio.paramValue, 'audio');
      expect(ContentType.pdf.paramValue, 'pdf');
    });
  });
}
