import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/widgets/text_search_bar.dart';

void main() {
  group('TextSearchBar', () {
    testWidgets('calls onChanged when text entered', (tester) async {
      String? captured;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextSearchBar(
              keyword: '',
              matchCount: 0,
              currentIndex: -1,
              onChanged: (value) => captured = value,
              onPrevious: () {},
              onNext: () {},
            ),
          ),
        ),
      );

      await tester.enterText(
        find.byKey(const Key('content_search_field')),
        'query',
      );
      await tester.pump();

      expect(captured, 'query');
    });

    testWidgets('shows match count and navigation buttons', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextSearchBar(
              keyword: 'test',
              matchCount: 3,
              currentIndex: 1,
              onChanged: (_) {},
              onPrevious: () {},
              onNext: () {},
            ),
          ),
        ),
      );

      expect(find.text('2 / 3'), findsOneWidget);
      expect(find.byKey(const Key('content_search_previous')), findsOneWidget);
      expect(find.byKey(const Key('content_search_next')), findsOneWidget);
    });

    testWidgets('shows no results text when matchCount is zero', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextSearchBar(
              keyword: 'test',
              matchCount: 0,
              currentIndex: -1,
              onChanged: (_) {},
              onPrevious: () {},
              onNext: () {},
            ),
          ),
        ),
      );

      expect(find.text('无结果'), findsOneWidget);
    });

    testWidgets('previous and next buttons invoke callbacks', (tester) async {
      var previousCount = 0;
      var nextCount = 0;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextSearchBar(
              keyword: 'test',
              matchCount: 2,
              currentIndex: 0,
              onChanged: (_) {},
              onPrevious: () => previousCount++,
              onNext: () => nextCount++,
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('content_search_previous')));
      await tester.tap(find.byKey(const Key('content_search_next')));
      await tester.pump();

      expect(previousCount, 1);
      expect(nextCount, 1);
    });
  });
}
