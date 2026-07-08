import 'package:flutter/material.dart';

/// Linear progress indicator for upload progress.
class UploadProgressBar extends StatelessWidget {
  const UploadProgressBar({
    required this.progress,
    this.height = 8,
    super.key,
  });

  /// Progress value between 0 and 100.
  final int progress;
  final double height;

  @override
  Widget build(BuildContext context) {
    final clamped = progress.clamp(0, 100);
    final value = clamped / 100;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(height / 2),
          child: LinearProgressIndicator(
            value: value,
            minHeight: height,
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
          ),
        ),
        const SizedBox(height: 4),
        Text('$clamped%', style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
