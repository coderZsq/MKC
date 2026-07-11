import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/conversation.dart';

void main() {
  group('Conversation', () {
    test('copyWith updates title and timestamps', () {
      final conversation = Conversation(
        id: 'c1',
        title: 'old',
        createdAt: DateTime(2024, 1, 1),
        updatedAt: DateTime(2024, 1, 1),
      );
      final updated = conversation.copyWith(
        title: 'new',
        updatedAt: DateTime(2024, 1, 2),
      );

      expect(updated.title, 'new');
      expect(updated.updatedAt, DateTime(2024, 1, 2));
      expect(updated.id, conversation.id);
      expect(updated.createdAt, conversation.createdAt);
    });
  });
}
