import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/task_result_model.dart';
import 'package:mkc_client/domain/entities/task.dart';

void main() {
  group('TaskResultModel', () {
    test('parses completed status from JSON', () {
      final model = TaskResultModel.fromJson({
        'task_id': 't1',
        'status': 'completed',
        'files': {
          'subtitle_url': 'https://example.com/sub.srt',
        },
        'metadata': {'key': 'value'},
      });

      expect(model.taskId, 't1');
      expect(model.status, TaskStatus.completed);
      expect(model.files.subtitleUrl, 'https://example.com/sub.srt');
      expect(model.metadata['key'], 'value');
    });

    test('defaults to pending for unknown status string', () {
      final model = TaskResultModel.fromJson({
        'task_id': 't2',
        'status': 'unknown_state',
        'files': <String, dynamic>{},
      });

      expect(model.status, TaskStatus.pending);
    });

    test('serializes to JSON with status name', () {
      const model = TaskResultModel(
        taskId: 't3',
        status: TaskStatus.failed,
        files: ResultFiles(
          parsedUrl: 'https://example.com/parsed.json',
        ),
      );

      final json = model.toJson();

      expect(json['task_id'], 't3');
      expect(json['status'], 'failed');
      expect(json['files']['parsed_url'], 'https://example.com/parsed.json');
    });

    test('copyWith updates fields immutably', () {
      const model = TaskResultModel(
        taskId: 't4',
        status: TaskStatus.pending,
        files: ResultFiles(),
      );

      final updated = model.copyWith(
        status: TaskStatus.completed,
        files: const ResultFiles(subtitleUrl: 'https://example.com/sub.srt'),
      );

      expect(updated.status, TaskStatus.completed);
      expect(updated.files.subtitleUrl, 'https://example.com/sub.srt');
      expect(model.status, TaskStatus.pending);
      expect(model.files.subtitleUrl, isNull);
    });
  });
}
