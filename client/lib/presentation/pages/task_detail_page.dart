import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/task.dart';
import '../providers/task_detail_provider.dart';
import '../providers/task_sse_provider.dart';
import '../widgets/claude_layout.dart';
import '../widgets/task_center_skeleton.dart';
import '../widgets/task_status_chip.dart';

/// Page displaying detailed information for a single task.
class TaskDetailPage extends ConsumerStatefulWidget {
  const TaskDetailPage({required this.taskId, super.key});

  final String taskId;

  @override
  ConsumerState<TaskDetailPage> createState() => _TaskDetailPageState();
}

class _TaskDetailPageState extends ConsumerState<TaskDetailPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(taskDetailNotifierProvider(widget.taskId).notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(taskDetailNotifierProvider(widget.taskId));
    final task = state.task;
    if (task != null &&
        (task.status == TaskStatus.pending ||
            task.status == TaskStatus.running)) {
      ref.listen(taskEventStreamProvider(task.id), (_, next) {
        final event = next.valueOrNull;
        if (event != null) {
          ref
              .read(taskDetailNotifierProvider(widget.taskId).notifier)
              .applyTaskEvent(event);
        }
      });
    }

    return Scaffold(
      appBar: AppBar(title: const Text('任务详情')),
      body: _buildBody(context, state),
    );
  }

  Widget _buildBody(BuildContext context, TaskDetailState state) {
    if (state.isLoading) {
      return const TaskCenterSkeleton();
    }

    final error = state.error;
    if (error != null) {
      return ClaudeEmptyState(
        title: error.message,
        icon: Icons.error_outline,
        action: ElevatedButton(
          onPressed: () => ref
              .read(taskDetailNotifierProvider(widget.taskId).notifier)
              .load(),
          child: const Text('重试'),
        ),
      );
    }

    final task = state.task;
    if (task == null) {
      return const ClaudeEmptyState(title: '任务不存在', icon: Icons.task_alt);
    }

    return ClaudePage(
      maxWidth: 840,
      children: [
        ClaudeSectionHeader(
          label: 'Task detail',
          title: task.resourceName,
          description: '任务状态、资源来源和更新时间。',
        ),
        const SizedBox(height: 24),
        ClaudePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  TaskStatusChip(status: task.status),
                  const SizedBox(width: 12),
                  Text(task.type.label),
                ],
              ),
              const SizedBox(height: 24),
              _InfoRow(label: '任务 ID', value: task.id),
              _InfoRow(label: '资源 ID', value: task.resourceId),
              _InfoRow(
                  label: '更新时间', value: formatTaskUpdatedAt(task.updatedAt)),
              if (task.status == TaskStatus.running ||
                  task.status == TaskStatus.pending) ...[
                const SizedBox(height: 24),
                LinearProgressIndicator(value: task.progress / 100),
                const SizedBox(height: 8),
                Text('进度: ${task.progress}%'),
              ],
              if (task.errorMessage != null &&
                  task.errorMessage!.isNotEmpty) ...[
                const SizedBox(height: 24),
                Text('错误信息:', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Text(task.errorMessage!,
                    style: const TextStyle(color: Colors.red)),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
              width: 80,
              child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
