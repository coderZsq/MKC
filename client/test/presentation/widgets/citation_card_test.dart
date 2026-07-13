import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/message.dart';
import 'package:mkc_client/presentation/widgets/citation_card.dart';

void main() {
  group('CitationCard', () {
    testWidgets('renders resource name with page', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CitationCard(
              citation: Citation(
                resourceId: 'res-1',
                resourceName: 'doc.pdf',
                index: 1,
                score: 0.9,
                page: '12',
              ),
            ),
          ),
        ),
      );

      expect(find.text('[^1] doc.pdf 第 12 页'), findsOneWidget);
      expect(find.byType(ActionChip), findsOneWidget);
    });

    testWidgets('renders resource name with timestamp', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CitationCard(
              citation: Citation(
                resourceId: 'res-2',
                resourceName: 'audio.mp3',
                index: 2,
                score: 0.8,
                timestamp: Duration(seconds: 75),
                timestampEnd: Duration(seconds: 90),
              ),
            ),
          ),
        ),
      );

      expect(find.text('[^2] audio.mp3 01:15-01:30'), findsOneWidget);
    });

    testWidgets('exposes snippet in tooltip', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CitationCard(
              citation: Citation(
                resourceId: 'res-3',
                resourceName: 'doc.pdf',
                score: 0.8,
                page: '3',
                snippet: 'quoted source text',
              ),
            ),
          ),
        ),
      );

      final gesture =
          await tester.startGesture(tester.getCenter(find.byType(ActionChip)));
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('quoted source text'), findsOneWidget);
      await gesture.up();
    });
  });
}
