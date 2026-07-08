import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/pages/task_center_page.dart';
import 'package:mkc_client/presentation/providers/task_center_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../shared/task_test_helpers.dart';

void main() {
  group('TaskCenterPage', () {
    late FakeTaskRepository repository;
    late TaskCenterNotifier notifier;

    setUp(() {
      repository = FakeTaskRepository();
      notifier = TaskCenterNotifier(repository: repository);
    });


    Future<void> pumpPage(WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskCenterNotifierProvider.overrideWith((ref) => notifier),
          ],
          child: const MaterialApp(home: TaskCenterPage()),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('renders empty state', (tester) async {
      repository.nextTasksResult = const Result.success([]);
      await pumpPage(tester);

      expect(find.text('暂无任务'), findsOneWidget);
    });

    testWidgets('renders task list', (tester) async {
      repository.nextTasksResult = Result.success([
        createTask(id: 't1', resourceName: 'report.pdf'),
      ]);
      await pumpPage(tester);

      expect(find.text('report.pdf'), findsOneWidget);
      expect(find.text('PDF 解析'), findsOneWidget);
    });

    testWidgets('renders error state with retry button', (tester) async {
      repository.nextTasksResult = const Result.failure(NetworkException());
      await pumpPage(tester);

      expect(find.text(const NetworkException().message), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });
  });
}
