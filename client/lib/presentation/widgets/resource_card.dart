import 'package:flutter/material.dart';

import '../../domain/entities/resource.dart';
import 'claude_layout.dart';
import 'resource_summary_text.dart';
import 'tag_chip_row.dart';

/// Resource list card with title, status, summary and tags.
class ResourceCard extends StatelessWidget {
  const ResourceCard({
    required this.resource,
    required this.onTap,
    required this.onTagTap,
    this.onAskTap,
    this.isAskLoading = false,
    super.key,
  });

  final Resource resource;
  final VoidCallback? onTap;
  final VoidCallback? onAskTap;
  final ValueChanged<String> onTagTap;
  final bool isAskLoading;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: ClaudePanel(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: onTap,
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      resource.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                  const SizedBox(width: 12),
                  _ResourceStatusChip(status: resource.status),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: resource.status == 'completed' && !isAskLoading
                    ? onAskTap
                    : null,
                icon: isAskLoading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.chat_bubble_outline, size: 18),
                label: const Text('问答'),
              ),
            ),
            const SizedBox(height: 10),
            ResourceSummaryText(
              summary: resource.summary,
              truncated: resource.summaryTruncated,
            ),
            const SizedBox(height: 8),
            TagChipRow(tags: resource.tags, onTagTap: onTagTap),
          ],
        ),
      ),
    );
  }
}

class _ResourceStatusChip extends StatelessWidget {
  const _ResourceStatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final label = switch (status) {
      'completed' => '已完成',
      'processing' => '处理中',
      'uploading' => '上传中',
      'failed' => '失败',
      _ => status,
    };
    final color = switch (status) {
      'completed' => Colors.green,
      'failed' => theme.colorScheme.error,
      'processing' || 'uploading' => theme.colorScheme.primary,
      _ => theme.colorScheme.outline,
    };
    return Chip(
      label: Text(label),
      visualDensity: VisualDensity.compact,
      side: BorderSide(color: color.withAlpha(102)),
      backgroundColor: color.withAlpha(26),
      labelStyle: theme.textTheme.labelSmall?.copyWith(color: color),
    );
  }
}
