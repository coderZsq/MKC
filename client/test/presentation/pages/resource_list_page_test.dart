import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/pages/resource_list_page.dart';
import 'package:mkc_client/presentation/providers/resource_list_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/resource_test_helpers.dart';

void main() {
  group('ResourceListPage', () {
    late FakeResourceRepository repository;

    setUp(() {
      repository = FakeResourceRepository();
    });

    Future<void> pumpPage(WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            resourceRepositoryProvider.overrideWithValue(repository),
          ],
          child: const MaterialApp(home: ResourceListPage()),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('renders resource summary and tags', (tester) async {
      repository.nextResourcesResult = Result.success([
        createResource(
            name: 'report.pdf', summary: '项目摘要', tags: const ['路线图']),
      ]);

      await pumpPage(tester);

      expect(find.text('report.pdf'), findsOneWidget);
      expect(find.text('项目摘要'), findsOneWidget);
      expect(find.text('路线图'), findsOneWidget);
    });

    testWidgets('renders empty state', (tester) async {
      repository.nextResourcesResult = const Result.success([]);

      await pumpPage(tester);

      expect(find.text('暂无资源'), findsOneWidget);
    });

    testWidgets('renders error state with retry', (tester) async {
      repository.nextResourcesResult = const Result.failure(NetworkException());

      await pumpPage(tester);

      expect(find.text(const NetworkException().message), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('filters by tag and clears filter', (tester) async {
      repository.nextResourcesResult = Result.success([
        createResource(id: 'all', name: 'all.pdf', tags: const ['AI']),
      ]);
      repository.tagResults['AI'] = Result.success([
        createResource(
            id: 'filtered', name: 'filtered.pdf', tags: const ['AI']),
      ]);

      await pumpPage(tester);
      await tester.tap(find.text('AI'));
      await tester.pumpAndSettle();

      expect(find.text('当前筛选：AI'), findsOneWidget);
      expect(find.text('filtered.pdf'), findsOneWidget);

      await tester.tap(find.text('清除筛选'));
      await tester.pumpAndSettle();

      expect(find.text('当前筛选：AI'), findsNothing);
      expect(repository.lastTag, isNull);
    });

    testWidgets('shows no match state for empty filtered result',
        (tester) async {
      repository.nextResourcesResult = Result.success([
        createResource(tags: const ['AI']),
      ]);
      repository.tagResults['AI'] = const Result.success([]);

      await pumpPage(tester);
      await tester.tap(find.text('AI'));
      await tester.pumpAndSettle();

      expect(find.text('无匹配资源'), findsOneWidget);
      expect(find.text('清除筛选'), findsWidgets);
    });

    testWidgets('keeps list and shows filter error on tag failure',
        (tester) async {
      repository.nextResourcesResult = Result.success([
        createResource(name: 'old.pdf', tags: const ['AI']),
      ]);
      repository.tagResults['AI'] = const Result.failure(NetworkException());

      await pumpPage(tester);
      await tester.tap(find.text('AI'));
      await tester.pumpAndSettle();

      expect(find.text('old.pdf'), findsOneWidget);
      expect(find.text('筛选失败，请重试'), findsOneWidget);
    });
  });
}
