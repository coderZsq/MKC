import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../domain/entities/task.dart';
import '../providers/task_center_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/claude_layout.dart';
import '../widgets/task_center_skeleton.dart';
import '../widgets/task_list_item.dart';

/// Page displaying the current user's task list.
class TaskCenterPage extends ConsumerStatefulWidget {
  const TaskCenterPage({super.key});

  @override
  ConsumerState<TaskCenterPage> createState() => _TaskCenterPageState();
}

class _TaskCenterPageState extends ConsumerState<TaskCenterPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(taskCenterNotifierProvider.notifier).loadInitial();
    });
  }

  Future<void> _onRefresh() async {
    await ref.read(taskCenterNotifierProvider.notifier).refresh();
  }

  String _contentTypeParam(TaskType type) {
    return switch (type) {
      TaskType.mediaParse => 'audio',
      TaskType.pdfParse || TaskType.documentParse => 'pdf',
    };
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(taskCenterNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('任务中心')),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 28, 24, 16),
            child: ClaudeSectionHeader(
              label: 'Tasks',
              title: '任务中心',
              description: '跟踪解析任务状态，并在完成后进入相应资源内容。',
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _onRefresh,
              child: _buildBody(state),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(TaskCenterState state) {
    if (state.isLoading && state.tasks.isEmpty) {
      return const TaskCenterSkeleton();
    }

    final error = state.error;
    if (error != null && state.tasks.isEmpty) {
      return ClaudeEmptyState(
        title: error.message,
        icon: Icons.error_outline,
        action: ElevatedButton(
          onPressed: _onRefresh,
          child: const Text('重试'),
        ),
      );
    }

    if (state.tasks.isEmpty) {
      return const ClaudeEmptyState(title: '暂无任务', icon: Icons.task_alt);
    }

    return ClaudeListShell(
      padding: EdgeInsets.zero,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
        itemCount: state.tasks.length + (state.hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == state.tasks.length) {
            if (!state.isLoadingMore) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (mounted) {
                  ref.read(taskCenterNotifierProvider.notifier).loadMore();
                }
              });
            }
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          final task = state.tasks[index];
          return TaskListItem(
            task: task,
            onTaskEvent:
                ref.read(taskCenterNotifierProvider.notifier).applyTaskEvent,
            onTap: () => context.go('$taskCenterRoute/${task.id}'),
            onViewContent: task.status == TaskStatus.completed
                ? () => context.push(
                      '${contentViewRoute.replaceFirst(':id', task.resourceId)}?type=${_contentTypeParam(task.type)}',
                    )
                : null,
          );
        },
      ),
    );
  }
}
