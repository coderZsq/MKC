import 'package:flutter/material.dart';

import '../../domain/entities/resource.dart';
import 'resource_summary_text.dart';
import 'tag_chip_row.dart';

/// Resource list card with title, status, summary and tags.
class ResourceCard extends StatelessWidget {
  const ResourceCard({
    required this.resource,
    required this.onTap,
    required this.onTagTap,
    super.key,
  });

  final Resource resource;
  final VoidCallback onTap;
  final ValueChanged<String> onTagTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      resource.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  _ResourceStatusChip(status: resource.status),
                ],
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
