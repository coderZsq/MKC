import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/chat_event.dart';

void main() {
  group('ChatEvent', () {
    test('isTerminal is true for done and error events', () {
      expect(const ChatEvent(type: 'done', messageId: 'm1').isTerminal, isTrue);
      expect(const ChatEvent(type: 'error', messageId: 'm1').isTerminal, isTrue);
      expect(const ChatEvent(type: 'chunk', messageId: 'm1').isTerminal, isFalse);
      expect(const ChatEvent(type: 'citation', messageId: 'm1').isTerminal, isFalse);
    });
  });
}
