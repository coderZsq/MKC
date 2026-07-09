import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/widgets/highlight_text.dart';

List<TextSpan> _findTextSpans(WidgetTester tester) {
  final richText = tester.widget<Text>(find.byType(Text));
  final textSpan = richText.textSpan as TextSpan?;
  if (textSpan == null) return const [];
  final children = textSpan.children;
  if (children == null) return [textSpan];
  return children.whereType<TextSpan>().toList();
}

void main() {
  group('HighlightText', () {
    testWidgets('renders plain text when keyword empty', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: HighlightText(text: 'plain text')),
        ),
      );

      expect(find.text('plain text'), findsOneWidget);
    });

    testWidgets('renders highlighted keyword occurrences', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: HighlightText(text: 'Hello world', keyword: 'world'),
          ),
        ),
      );

      final spans = _findTextSpans(tester);
      expect(spans.map((s) => s.text).toList(), ['Hello ', 'world']);
    });

    testWidgets('is case-insensitive', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: HighlightText(text: 'Hello World', keyword: 'world'),
          ),
        ),
      );

      final spans = _findTextSpans(tester);
      expect(spans.map((s) => s.text).toList(), ['Hello ', 'World']);
    });

    testWidgets('active match uses highlight colors', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: HighlightText(
              text: 'Hello world',
              keyword: 'world',
              highlightStart: 6,
              highlightEnd: 11,
            ),
          ),
        ),
      );

      final spans = _findTextSpans(tester);
      final activeSpan = spans.firstWhere((s) => s.text == 'world');
      final theme = Theme.of(tester.element(find.byType(HighlightText)));
      expect(activeSpan.style?.backgroundColor, theme.colorScheme.primary);
      expect(activeSpan.style?.color, theme.colorScheme.onPrimary);
    });
  });
}
