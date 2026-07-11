import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/presentation/widgets/chat_bubble.dart';

import '../../shared/chat_test_helpers.dart';

void main() {
  group('ChatBubble', () {
    testWidgets('renders user content as plain text', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: createMessage(
                role: MessageRole.user,
                content: 'User question',
              ),
            ),
          ),
        ),
      );

      expect(find.text('User question'), findsOneWidget);
    });

    testWidgets('renders assistant content as markdown', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: createMessage(
                role: MessageRole.assistant,
                content: '**bold** answer',
                citations: const [
                  Citation(
                    resourceId: 'res-1',
                    resourceName: 'doc.pdf',
                    score: 0.9,
                  ),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('bold answer'), findsOneWidget);
      expect(find.text('doc.pdf'), findsOneWidget);
    });
  });
}
