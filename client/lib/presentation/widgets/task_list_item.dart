import 'package:flutter/material.dart';

import '../../../domain/entities/task.dart';
import 'task_status_chip.dart';

/// List item rendering a single task summary.
class TaskListItem extends StatelessWidget {
  const TaskListItem({required this.task, this.onTap, super.key});

  final Task task;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
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
                      task.resourceName,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  TaskStatusChip(status: task.status),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    task.type.label,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    formatTaskUpdatedAt(task.updatedAt),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              if (task.status == TaskStatus.running || task.status == TaskStatus.pending) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(value: task.progress / 100),
                const SizedBox(height: 4),
                Text('${task.progress}%', style: Theme.of(context).textTheme.bodySmall),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
