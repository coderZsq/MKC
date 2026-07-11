import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/widgets/streaming_indicator.dart';

void main() {
  group('StreamingIndicator', () {
    testWidgets('renders progress indicator and label', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: StreamingIndicator()),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('AI is thinking'), findsOneWidget);
    });
  });
}
