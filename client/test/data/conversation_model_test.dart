import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/conversation_model.dart';

void main() {
  group('ConversationModel.fromJson', () {
    test('parses id and falls back to conversation_id', () {
      final byId = ConversationModel.fromJson(const {
        'id': 'conv-1',
        'title': 'Chat',
        'created_at': 1700000000,
        'updated_at': 1700000001,
      });
      expect(byId.conversationId, 'conv-1');

      final byConversationId = ConversationModel.fromJson(const {
        'conversation_id': 'conv-2',
        'title': 'Other',
        'created_at': 1700000000,
        'updated_at': 1700000001,
      });
      expect(byConversationId.conversationId, 'conv-2');
    });

    test('parses resource_ids and model_config', () {
      final model = ConversationModel.fromJson(const {
        'id': 'conv-3',
        'title': 'Resource chat',
        'resource_ids': ['res-1', 'res-2'],
        'model_config': {'model': 'glm-4'},
        'created_at': 1700000000,
        'updated_at': 1700000001,
      });

      expect(model.title, 'Resource chat');
      expect(model.resourceIds, ['res-1', 'res-2']);
      expect(model.modelConfig, {'model': 'glm-4'});
    });

    test('defaults missing fields safely', () {
      final model = ConversationModel.fromJson(const {
        'id': 'conv-4',
        'created_at': 1700000000,
        'updated_at': 1700000001,
      });

      expect(model.title, '');
      expect(model.resourceIds, isEmpty);
      expect(model.modelConfig, isNull);
    });

    test('maps to domain entity correctly', () {
      final model = ConversationModel.fromJson(const {
        'id': 'conv-5',
        'title': 'Domain',
        'resource_ids': ['res-1'],
        'model_config': {'temperature': 0.7},
        'created_at': 1700000000,
        'updated_at': 1700000001,
      });

      final entity = model.toDomain();
      expect(entity.id, 'conv-5');
      expect(entity.title, 'Domain');
      expect(entity.resourceIds, ['res-1']);
      expect(entity.modelConfig, {'temperature': 0.7});
      expect(entity.createdAt, DateTime.fromMillisecondsSinceEpoch(1700000000 * 1000));
      expect(entity.updatedAt, DateTime.fromMillisecondsSinceEpoch(1700000001 * 1000));
    });
  });
}
