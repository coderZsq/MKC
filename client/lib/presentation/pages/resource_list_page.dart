import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/resource_list_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/resource_card.dart';

/// Page displaying resource cards with summaries and tags.
class ResourceListPage extends ConsumerStatefulWidget {
  const ResourceListPage({super.key});

  @override
  ConsumerState<ResourceListPage> createState() => _ResourceListPageState();
}

class _ResourceListPageState extends ConsumerState<ResourceListPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(resourceListNotifierProvider.notifier).loadInitial();
    });
  }

  Future<void> _refresh() async {
    await ref.read(resourceListNotifierProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(resourceListNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('资源库')),
      body: Column(
        children: [
          if (state.selectedTag != null)
            _ActiveTagFilterBar(
              tag: state.selectedTag!,
              onClear: () =>
                  ref.read(resourceListNotifierProvider.notifier).clearFilter(),
            ),
          if (state.filterError != null)
            const _InlineError(message: '筛选失败，请重试'),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: _buildBody(state),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(ResourceListState state) {
    if (state.isLoading && state.resources.isEmpty) {
      return const _ResourceListSkeleton();
    }

    if (state.error != null && state.resources.isEmpty) {
      return _CenteredState(
        message: state.error!.message,
        actionLabel: '重试',
        onPressed: _refresh,
      );
    }

    if (state.resources.isEmpty) {
      return _CenteredState(
        message: state.selectedTag == null ? '暂无资源' : '无匹配资源',
        actionLabel: state.selectedTag == null ? null : '清除筛选',
        onPressed: state.selectedTag == null
            ? null
            : () =>
                ref.read(resourceListNotifierProvider.notifier).clearFilter(),
      );
    }

    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: state.resources.length + (state.hasMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == state.resources.length) {
          if (!state.isLoadingMore) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) {
                ref.read(resourceListNotifierProvider.notifier).loadMore();
              }
            });
          }
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          );
        }

        final resource = state.resources[index];
        return ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: ResourceCard(
            resource: resource,
            onTap: resource.taskId == null || resource.taskId!.isEmpty
                ? null
                : () => context.push(
                      '${contentViewRoute.replaceFirst(':id', resource.taskId!)}?type=${_contentTypeParam(resource.type)}',
                    ),
            onTagTap:
                ref.read(resourceListNotifierProvider.notifier).filterByTag,
          ),
        );
      },
    );
  }

  String _contentTypeParam(String type) {
    if (type.contains('media') || type == 'audio') return 'audio';
    return 'pdf';
  }
}

class _ActiveTagFilterBar extends StatelessWidget {
  const _ActiveTagFilterBar({required this.tag, required this.onClear});

  final String tag;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: theme.colorScheme.secondaryContainer.withAlpha(128),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            Icon(Icons.filter_alt_outlined,
                size: 18, color: theme.colorScheme.onSecondaryContainer),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '当前筛选：$tag',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium,
              ),
            ),
            TextButton(onPressed: onClear, child: const Text('清除筛选')),
          ],
        ),
      ),
    );
  }
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: theme.colorScheme.errorContainer,
      child: Text(
        message,
        style: theme.textTheme.bodySmall
            ?.copyWith(color: theme.colorScheme.onErrorContainer),
      ),
    );
  }
}

class _CenteredState extends StatelessWidget {
  const _CenteredState({
    required this.message,
    this.actionLabel,
    this.onPressed,
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 160),
        Center(child: Text(message)),
        if (actionLabel != null && onPressed != null) ...[
          const SizedBox(height: 16),
          Center(
            child: OutlinedButton(
              onPressed: onPressed,
              child: Text(actionLabel!),
            ),
          ),
        ],
      ],
    );
  }
}

class _ResourceListSkeleton extends StatelessWidget {
  const _ResourceListSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: 4,
      itemBuilder: (context, index) => const Card(
        margin: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: SizedBox(height: 128),
      ),
    );
  }
}
