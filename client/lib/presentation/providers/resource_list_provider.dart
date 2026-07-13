import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/datasources/remote/resource_api.dart';
import '../../data/repositories/resource_repository.dart';
import '../../domain/entities/resource.dart';
import '../../domain/repositories/resource_repository.dart';
import '../../shared/errors/app_exception.dart';
import 'app_provider.dart';

const int defaultResourcePageSize = 20;

/// UI state for the resource list.
class ResourceListState {
  const ResourceListState({
    this.resources = const <Resource>[],
    this.currentPage = 1,
    this.hasMore = true,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.selectedTag,
    this.error,
    this.filterError,
  });

  final List<Resource> resources;
  final int currentPage;
  final bool hasMore;
  final bool isLoading;
  final bool isLoadingMore;
  final String? selectedTag;
  final AppException? error;
  final AppException? filterError;

  ResourceListState copyWith({
    List<Resource>? resources,
    int? currentPage,
    bool? hasMore,
    bool? isLoading,
    bool? isLoadingMore,
    String? selectedTag,
    bool clearSelectedTag = false,
    AppException? error,
    AppException? filterError,
    bool clearError = false,
    bool clearFilterError = false,
  }) {
    return ResourceListState(
      resources: resources ?? this.resources,
      currentPage: currentPage ?? this.currentPage,
      hasMore: hasMore ?? this.hasMore,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      selectedTag: clearSelectedTag ? null : selectedTag ?? this.selectedTag,
      error: clearError ? null : error,
      filterError: clearFilterError ? null : filterError,
    );
  }
}

/// Manages resource list pagination, refresh and tag filtering.
class ResourceListNotifier extends StateNotifier<ResourceListState> {
  ResourceListNotifier({required ResourceRepository repository})
      : _repository = repository,
        super(const ResourceListState());

  final ResourceRepository _repository;

  Future<void> loadInitial() async {
    state = state.copyWith(
      isLoading: true,
      currentPage: 1,
      hasMore: true,
      clearError: true,
      clearFilterError: true,
    );
    final result = await _repository.fetchResources(
      page: 1,
      limit: defaultResourcePageSize,
      tag: state.selectedTag,
    );
    state = result.when(
      success: (resources) => state.copyWith(
        isLoading: false,
        resources: resources,
        currentPage: 1,
        hasMore: resources.length == defaultResourcePageSize,
        clearError: true,
      ),
      failure: (error) => state.copyWith(isLoading: false, error: error),
    );
  }

  Future<void> refresh() async {
    await loadInitial();
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;

    final nextPage = state.currentPage + 1;
    state = state.copyWith(isLoadingMore: true, clearFilterError: true);
    final result = await _repository.fetchResources(
      page: nextPage,
      limit: defaultResourcePageSize,
      tag: state.selectedTag,
    );
    state = result.when(
      success: (resources) => state.copyWith(
        isLoadingMore: false,
        resources: <Resource>[...state.resources, ...resources],
        currentPage: nextPage,
        hasMore: resources.length == defaultResourcePageSize,
      ),
      failure: (error) => state.copyWith(
        isLoadingMore: false,
        filterError: error,
      ),
    );
  }

  Future<void> filterByTag(String tag) async {
    final previous = state;
    state = state.copyWith(
      selectedTag: tag,
      isLoading: true,
      currentPage: 1,
      clearError: true,
      clearFilterError: true,
    );
    final result = await _repository.fetchResources(
      page: 1,
      limit: defaultResourcePageSize,
      tag: tag,
    );
    state = result.when(
      success: (resources) => state.copyWith(
        isLoading: false,
        resources: resources,
        currentPage: 1,
        hasMore: resources.length == defaultResourcePageSize,
      ),
      failure: (error) => previous.copyWith(
        selectedTag: tag,
        isLoading: false,
        filterError: error,
      ),
    );
  }

  Future<void> clearFilter() async {
    state = state.copyWith(clearSelectedTag: true);
    await loadInitial();
  }
}

final resourceApiProvider = Provider<ResourceApi>((ref) {
  return ResourceApi(client: ref.watch(apiClientProvider));
});

final resourceRepositoryProvider = Provider<ResourceRepository>((ref) {
  return ResourceRepositoryImpl(api: ref.watch(resourceApiProvider));
});

final resourceListNotifierProvider =
    StateNotifierProvider.autoDispose<ResourceListNotifier, ResourceListState>(
  (ref) =>
      ResourceListNotifier(repository: ref.watch(resourceRepositoryProvider)),
);
