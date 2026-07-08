import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../domain/entities/task.dart';
import '../providers/task_sse_provider.dart';
import 'task_status_chip.dart';

/// List item rendering a single task summary.
class TaskListItem extends ConsumerWidget {
  const TaskListItem({required this.task, this.onTap, super.key});

  final Task task;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final displayTask = task.status == TaskStatus.running
        ? taskWithEvent(task, ref.watch(taskEventStreamProvider(task.id)))
        : task;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
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
                Text('${displayTask.progress}%', style: Theme.of(context).textTheme.bodySmall),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
