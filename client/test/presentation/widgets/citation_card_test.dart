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
                score: 0.9,
                page: '12',
              ),
            ),
          ),
        ),
      );

      expect(find.text('doc.pdf P12'), findsOneWidget);
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
                score: 0.8,
                timestamp: Duration(seconds: 75),
              ),
            ),
          ),
        ),
      );

      expect(find.text('audio.mp3 00:01:15'), findsOneWidget);
    });
  });
}
