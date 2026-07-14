import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/message_model.dart';
import 'package:mkc_client/domain/entities/content_type.dart';

void main() {
  group('MessageModel', () {
    test('preserves reasoning and complete citation metadata', () {
      final model = MessageModel.fromJson({
        'id': 'm-1',
        'conversation_id': 'c-1',
        'role': 'assistant',
        'content': 'answer',
        'reasoning': 'thinking step',
        'citations': [
          {
            'index': 1,
            'chunk_id': 'chunk-1',
            'resource_id': 'res-1',
            'resource_name': 'doc.pdf',
            'resource_type': 'pdf',
            'page': 6,
            'snippet': 'quoted source',
            'score': 0.9,
          }
        ],
        'created_at': '2026-07-15T00:00:00Z',
      });

      final message = model.toDomain();

      expect(message.reasoning, 'thinking step');
      expect(message.citations, hasLength(1));
      expect(message.citations.first.index, 1);
      expect(message.citations.first.chunkId, 'chunk-1');
      expect(message.citations.first.page, '6');
      expect(message.citations.first.snippet, 'quoted source');
      expect(message.citations.first.contentType, ContentType.pdf);
    });
  });
}
