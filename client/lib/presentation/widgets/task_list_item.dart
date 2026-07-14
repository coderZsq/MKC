import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../domain/entities/task.dart';
import '../../../domain/entities/task_event.dart';
import '../providers/task_sse_provider.dart';
import 'claude_layout.dart';
import 'task_status_chip.dart';

/// List item rendering a single task summary.
class TaskListItem extends ConsumerWidget {
  const TaskListItem({
    required this.task,
    this.onTaskEvent,
    this.onTap,
    this.onViewContent,
    super.key,
  });

  final Task task;
  final ValueChanged<TaskEvent>? onTaskEvent;
  final VoidCallback? onTap;
  final VoidCallback? onViewContent;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shouldSubscribe =
        task.status == TaskStatus.running || task.status == TaskStatus.pending;
    final eventProvider = taskEventStreamProvider(task.id);

    if (shouldSubscribe && onTaskEvent != null) {
      ref.listen(eventProvider, (_, next) {
        final event = next.valueOrNull;
        if (event != null) {
          onTaskEvent!(event);
        }
      });
    }

    final displayTask =
        shouldSubscribe ? taskWithEvent(task, ref.watch(eventProvider)) : task;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: ClaudePanel(
        onTap: onTap,
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    displayTask.resourceName,
                    style: Theme.of(context).textTheme.titleMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                TaskStatusChip(status: displayTask.status),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  displayTask.type.label,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(width: 12),
                Text(
                  formatTaskUpdatedAt(displayTask.updatedAt),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            if (displayTask.status == TaskStatus.running ||
                displayTask.status == TaskStatus.pending) ...[
              const SizedBox(height: 12),
              LinearProgressIndicator(value: displayTask.progress / 100),
              const SizedBox(height: 4),
              Text('${displayTask.progress}%',
                  style: Theme.of(context).textTheme.bodySmall),
            ],
            if (onViewContent != null) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: onViewContent,
                  child: const Text('查看内容'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
