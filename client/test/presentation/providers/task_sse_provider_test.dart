import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/task_sse_client.dart';
import 'package:mkc_client/domain/entities/task.dart';
import 'package:mkc_client/domain/entities/task_event.dart';
import 'package:mkc_client/presentation/providers/task_sse_provider.dart';

import '../../shared/task_test_helpers.dart';

class _FakeTaskSseClient implements TaskSseClient {
  _FakeTaskSseClient({required this.controller});

  final StreamController<TaskEvent> controller;

  @override
  Stream<TaskEvent> subscribe(String taskId) => controller.stream;
}

void main() {
  group('taskWithEvent', () {
    test('returns original task when event is null', () {
      final task = createTask(id: 't1', status: TaskStatus.pending, progress: 0);
      final result = taskWithEvent(task, const AsyncValue<TaskEvent?>.data(null));

      expect(result.status, TaskStatus.pending);
      expect(result.progress, 0);
    });

    test('updates status, progress and error message from event', () {
      final task = createTask(id: 't1', status: TaskStatus.running, progress: 10);
      final event = TaskEvent(
        taskId: 't1',
        eventType: 'progress',
        status: 'running',
        progress: 55,
        timestamp: DateTime.now(),
      );

      final result = taskWithEvent(task, AsyncValue<TaskEvent?>.data(event));

      expect(result.status, TaskStatus.running);
      expect(result.progress, 55);
    });

    test('clamps progress to 100', () {
      final task = createTask(id: 't1', status: TaskStatus.running, progress: 10);
      final event = TaskEvent(
        taskId: 't1',
        eventType: 'progress',
        status: 'running',
        progress: 150,
        timestamp: DateTime.now(),
      );

      final result = taskWithEvent(task, AsyncValue<TaskEvent?>.data(event));

      expect(result.progress, 100);
    });

    test('returns original task on error', () {
      final task = createTask(id: 't1', status: TaskStatus.running, progress: 10);
      final result = taskWithEvent(
        task,
        const AsyncValue<TaskEvent?>.error('boom', StackTrace.empty),
      );

      expect(result.status, TaskStatus.running);
      expect(result.progress, 10);
    });
  });

  group('taskEventStreamProvider', () {
    late StreamController<TaskEvent> controller;

    setUp(() {
      controller = StreamController<TaskEvent>.broadcast();
    });

    tearDown(() {
      controller.close();
    });

    ProviderContainer createContainer() {
      return ProviderContainer(
        overrides: [
          taskSseClientProvider.overrideWithValue(
            _FakeTaskSseClient(controller: controller),
          ),
        ],
      );
    }

    test('emits events for the requested task', () async {
      final container = createContainer();
      addTearDown(container.dispose);

      final provider = taskEventStreamProvider('t1');
      // Start listening so the autoDispose provider stays alive.
      final sub = container.listen(provider, (_, __) {});
      addTearDown(sub.close);

      controller.add(
        TaskEvent(
          taskId: 't1',
          eventType: 'progress',
          status: 'running',
          progress: 20,
          timestamp: DateTime.now(),
        ),
      );

      final event = await container.read(provider.future);
      expect(event, isNotNull);
      expect(event!.taskId, 't1');
      expect(event.progress, 20);
    });

    test('filters events for other tasks', () async {
      final container = createContainer();
      addTearDown(container.dispose);

      final provider = taskEventStreamProvider('t1');
      final sub = container.listen(provider, (_, __) {});
      addTearDown(sub.close);

      controller.add(
        TaskEvent(
          taskId: 't2',
          eventType: 'progress',
          status: 'running',
          progress: 99,
          timestamp: DateTime.now(),
        ),
      );
      // Allow the stream to process the filtered event.
      await Future.delayed(const Duration(milliseconds: 50));
      expect(container.read(provider), const AsyncValue<TaskEvent?>.loading());

      controller.add(
        TaskEvent(
          taskId: 't1',
          eventType: 'progress',
          status: 'running',
          progress: 30,
          timestamp: DateTime.now(),
        ),
      );

      final event = await container.read(provider.future);
      expect(event, isNotNull);
      expect(event!.taskId, 't1');
      expect(event.progress, 30);
    });
  });
}
