import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/models/resource_model.dart';

void main() {
  test('maps summary and tags to domain resource', () {
    final model = ResourceModel.fromJson({
      'resource_id': 'res-1',
      'name': 'report.pdf',
      'type': 'pdf_parse',
      'status': 'completed',
      'summary': '摘要',
      'summary_truncated': true,
      'tags': ['机器学习', '', 1, 'AI'],
      'updated_at': '2026-07-12T10:30:00Z',
    });

    final resource = model.toDomain();

    expect(resource.id, 'res-1');
    expect(resource.summary, '摘要');
    expect(resource.summaryTruncated, isTrue);
    expect(resource.tags, ['机器学习', 'AI']);
  });

  test('handles missing summary and tags', () {
    final model = ResourceModel.fromJson({
      'resource_id': 'res-2',
      'name': 'audio.mp3',
      'type': 'media_parse',
      'status': 'completed',
    });

    expect(model.summary, isNull);
    expect(model.tags, isEmpty);
  });
}
