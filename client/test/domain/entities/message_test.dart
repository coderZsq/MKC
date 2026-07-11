import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/content_type.dart';
import 'package:mkc_client/domain/entities/message.dart';

void main() {
  group('MessageRole', () {
    test('parses assistant string', () {
      expect(MessageRole.fromString('assistant'), MessageRole.assistant);
    });

    test('defaults to user for unknown strings', () {
      expect(MessageRole.fromString('unknown'), MessageRole.user);
      expect(MessageRole.fromString('user'), MessageRole.user);
    });
  });

  group('Message', () {
    test('creates user message with content', () {
      final message = Message.user(
        id: 'm1',
        conversationId: 'c1',
        content: 'hello',
      );

      expect(message.role, MessageRole.user);
      expect(message.content, 'hello');
      expect(message.conversationId, 'c1');
      expect(message.isStreaming, isFalse);
      expect(message.citations, isEmpty);
    });

    test('creates streaming assistant message', () {
      final message = Message.assistant(
        id: 'm2',
        conversationId: 'c1',
        isStreaming: true,
      );

      expect(message.role, MessageRole.assistant);
      expect(message.content, isEmpty);
      expect(message.isStreaming, isTrue);
    });

    test('copyWith returns new instance with updated values', () {
      final message = Message.assistant(
        id: 'm1',
        conversationId: 'c1',
        content: 'partial',
      );
      final updated = message.copyWith(content: 'complete', isStreaming: false);

      expect(updated.content, 'complete');
      expect(updated.isStreaming, isFalse);
      expect(updated.id, message.id);
    });
  });

  group('Citation', () {
    test('defaults contentType to pdf', () {
      const citation = Citation(
        resourceId: 'r1',
        resourceName: 'doc.pdf',
        page: '3',
        score: 0.95,
      );

      expect(citation.contentType, ContentType.pdf);
      expect(citation.timestamp, isNull);
    });

    test('copyWith updates contentType', () {
      const citation = Citation(
        resourceId: 'r1',
        resourceName: 'song.mp3',
        score: 0.8,
      );
      final updated = citation.copyWith(contentType: ContentType.audio);

      expect(updated.contentType, ContentType.audio);
      expect(updated.resourceId, citation.resourceId);
    });
  });
}
