import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/providers/resource_list_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/resource_test_helpers.dart';

void main() {
  late FakeResourceRepository repository;
  late ResourceListNotifier notifier;

  setUp(() {
    repository = FakeResourceRepository();
    notifier = ResourceListNotifier(repository: repository);
  });

  tearDown(() {
    notifier.dispose();
  });

  test('loadInitial sets resources and pagination', () async {
    repository.nextResourcesResult = Result.success([createResource()]);

    await notifier.loadInitial();

    expect(notifier.state.resources, hasLength(1));
    expect(notifier.state.hasMore, isFalse);
    expect(repository.lastPage, 1);
    expect(repository.lastLimit, defaultResourcePageSize);
  });

  test('filterByTag replaces list and stores selected tag', () async {
    repository.nextResourcesResult =
        Result.success([createResource(id: 'all')]);
    await notifier.loadInitial();
    repository.tagResults['AI'] = Result.success([
      createResource(id: 'filtered', tags: const ['AI'])
    ]);

    await notifier.filterByTag('AI');

    expect(notifier.state.selectedTag, 'AI');
    expect(notifier.state.resources.single.id, 'filtered');
  });

  test('filter failure preserves previous list and exposes filterError',
      () async {
    repository.nextResourcesResult =
        Result.success([createResource(id: 'old')]);
    await notifier.loadInitial();
    repository.tagResults['AI'] = const Result.failure(NetworkException());

    await notifier.filterByTag('AI');

    expect(notifier.state.resources.single.id, 'old');
    expect(notifier.state.selectedTag, 'AI');
    expect(notifier.state.filterError, isA<NetworkException>());
  });

  test('clearFilter reloads full list', () async {
    repository.tagResults['AI'] =
        Result.success([createResource(id: 'filtered')]);
    await notifier.filterByTag('AI');
    repository.nextResourcesResult =
        Result.success([createResource(id: 'all')]);

    await notifier.clearFilter();

    expect(notifier.state.selectedTag, isNull);
    expect(notifier.state.resources.single.id, 'all');
  });
}
