import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/widgets/chat_input_bar.dart';

void main() {
  group('ChatInputBar', () {
    testWidgets('sends trimmed text when send button pressed', (tester) async {
      String? sent;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatInputBar(
              onSend: (text) => sent = text,
              enabled: true,
            ),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '  Hello  ');
      await tester.tap(find.byIcon(Icons.send));
      await tester.pump();

      expect(sent, 'Hello');
      expect(find.text(''), findsOneWidget);
    });

    testWidgets('does not send empty text', (tester) async {
      var calls = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatInputBar(
              onSend: (_) => calls++,
              enabled: true,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.send));
      await tester.pump();

      expect(calls, 0);
    });

    testWidgets('shows stop button and disables input while sending', (tester) async {
      var canceled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatInputBar(
              onSend: (_) {},
              onCancel: () => canceled = true,
              enabled: false,
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.stop), findsOneWidget);
      expect(find.byIcon(Icons.send), findsNothing);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);

      await tester.tap(find.byIcon(Icons.stop));
      await tester.pump();
      expect(canceled, isTrue);
    });
  });
}
