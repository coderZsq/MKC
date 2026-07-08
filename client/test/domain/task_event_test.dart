import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/domain/entities/task_event.dart';

void main() {
  group('TaskEvent.fromJson', () {
    test('parses progress event with provided event type', () {
      final event = TaskEvent.fromJson(
        <String, dynamic>{
          'task_id': 't1',
          'status': 'running',
          'progress': 42,
          'timestamp': '2024-01-01T12:00:00.000Z',
        },
        eventType: 'progress',
      );

      expect(event.taskId, 't1');
      expect(event.eventType, 'progress');
      expect(event.status, 'running');
      expect(event.progress, 42);
      expect(event.message, isNull);
    });

    test('defaults event type to status when omitted', () {
      final event = TaskEvent.fromJson(<String, dynamic>{
        'task_id': 't1',
        'status': 'pending',
        'progress': 0,
      });

      expect(event.eventType, 'status');
    });

    test('carries error message', () {
      final event = TaskEvent.fromJson(
        <String, dynamic>{
          'task_id': 't1',
          'status': 'failed',
          'progress': 0,
          'message': 'parse error',
          'timestamp': '2024-01-01T12:00:00.000Z',
        },
        eventType: 'error',
      );

      expect(event.eventType, 'error');
      expect(event.message, 'parse error');
    });

    test('uses defaults for missing fields', () {
      final event = TaskEvent.fromJson(<String, dynamic>{});

      expect(event.taskId, '');
      expect(event.status, '');
      expect(event.progress, 0);
      expect(event.eventType, 'status');
    });
  });
}
