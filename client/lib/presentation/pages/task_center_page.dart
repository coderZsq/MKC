import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/task_center_provider.dart';
import '../routes/app_routes.dart';
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

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(taskCenterNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('任务中心')),
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        child: _buildBody(state),
      ),
    );
  }

  Widget _buildBody(TaskCenterState state) {
    if (state.isLoading && state.tasks.isEmpty) {
      return const TaskCenterSkeleton();
    }

    final error = state.error;
    if (error != null && state.tasks.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(error.message),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _onRefresh,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (state.tasks.isEmpty) {
      return const Center(child: Text('暂无任务'));
    }

    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(vertical: 8),
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
          onTap: () => context.go('$taskCenterRoute/${task.id}'),
        );
      },
    );
  }
}
