import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/task_model.dart';
import 'package:mkc_client/domain/entities/task.dart';

void main() {
  group('TaskModel.fromJson', () {
    test('parses unix-second updated_at into DateTime', () {
      final model = TaskModel.fromJson(const {
        'task_id': 'task-1',
        'resource_id': 'res-1',
        'resource_name': 'report.pdf',
        'type': 'pdf_parse',
        'status': 'running',
        'progress': 42,
        'updated_at': 1700000000,
      });

      expect(model.taskId, 'task-1');
      expect(model.resourceName, 'report.pdf');
      expect(model.status, 'running');
      expect(model.progress, 42);
      expect(model.updatedAt, DateTime.fromMillisecondsSinceEpoch(1700000000 * 1000));
    });

    test('parses string updated_at as fallback', () {
      final model = TaskModel.fromJson(const {
        'task_id': 'task-2',
        'resource_id': 'res-2',
        'resource_name': 'clip.mp4',
        'type': 'media_parse',
        'status': 'completed',
        'progress': 100,
        'updated_at': '2024-06-15T10:30:00.000Z',
      });

      expect(model.type, 'media_parse');
      expect(model.status, 'completed');
      expect(model.updatedAt, DateTime.parse('2024-06-15T10:30:00.000Z'));
    });

    test('maps to domain entity correctly', () {
      final model = TaskModel.fromJson(const {
        'task_id': 'task-3',
        'resource_id': 'res-3',
        'resource_name': 'doc.docx',
        'type': 'document_parse',
        'status': 'failed',
        'progress': 0,
        'error_message': 'parse error',
        'updated_at': 1700000000,
      });

      final task = model.toDomain();
      expect(task.id, 'task-3');
      expect(task.type, TaskType.documentParse);
      expect(task.status, TaskStatus.failed);
      expect(task.errorMessage, 'parse error');
    });
  });
}
