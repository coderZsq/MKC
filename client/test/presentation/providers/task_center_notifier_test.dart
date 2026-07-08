import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/providers/task_center_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/task_test_helpers.dart';

void main() {
  late FakeTaskRepository repository;
  late TaskCenterNotifier notifier;

  setUp(() {
    repository = FakeTaskRepository();
    notifier = TaskCenterNotifier(repository: repository);
  });

  tearDown(() {
    notifier.dispose();
  });

  group('loadInitial', () {
    test('sets tasks and clears loading on success', () async {
      final tasks = [createTask(id: 't1'), createTask(id: 't2')];
      repository.nextTasksResult = Result.success(tasks);

      await notifier.loadInitial();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.tasks, hasLength(2));
      expect(notifier.state.tasks.first.id, 't1');
      expect(repository.lastPage, 1);
      expect(repository.lastLimit, 20);
    });

    test('sets error on failure', () async {
      repository.nextTasksResult = const Result.failure(NetworkException());

      await notifier.loadInitial();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, isA<NetworkException>());
      expect(notifier.state.tasks, isEmpty);
    });
  });

  group('loadMore', () {
    test('appends next page when hasMore is true', () async {
      final firstPage = List.generate(20, (i) => createTask(id: 't-$i'));
      repository.nextTasksResult = Result.success(firstPage);
      await notifier.loadInitial();

      final secondPage = [createTask(id: 't-20')];
      repository.nextTasksResult = Result.success(secondPage);
      await notifier.loadMore();

      expect(notifier.state.tasks, hasLength(21));
      expect(notifier.state.tasks.last.id, 't-20');
      expect(notifier.state.hasMore, isFalse);
      expect(repository.lastPage, 2);
    });

    test('does nothing when previous page had fewer than page size', () async {
      repository.nextTasksResult = Result.success([createTask(id: 't1')]);
      await notifier.loadInitial();

      repository.listCalls = 0;
      await notifier.loadMore();

      expect(repository.listCalls, 0);
    });
  });

  group('refresh', () {
    test('reloads first page', () async {
      repository.nextTasksResult = Result.success([createTask(id: 'old')]);
      await notifier.loadInitial();

      repository.nextTasksResult = Result.success([createTask(id: 'new')]);
      await notifier.refresh();

      expect(notifier.state.tasks, hasLength(1));
      expect(notifier.state.tasks.first.id, 'new');
    });
  });
}
