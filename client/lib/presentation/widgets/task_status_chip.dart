import 'package:flutter/material.dart';

import '../../../domain/entities/task.dart';

/// Colored chip displaying a task status label.
class TaskStatusChip extends StatelessWidget {
  const TaskStatusChip({required this.status, super.key});

  final TaskStatus status;

  @override
  Widget build(BuildContext context) {
    return Chip(
      visualDensity: VisualDensity.compact,
      backgroundColor: status.color.withAlpha(31),
      side: BorderSide(color: status.color.withAlpha(61)),
      label: Text(
        status.label,
        style: TextStyle(
          color: status.color,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
