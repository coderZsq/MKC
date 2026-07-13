import 'package:flutter/material.dart';

/// Two-line collapsible summary text for resource cards.
class ResourceSummaryText extends StatefulWidget {
  const ResourceSummaryText({
    required this.summary,
    required this.truncated,
    super.key,
  });

  final String? summary;
  final bool truncated;

  @override
  State<ResourceSummaryText> createState() => _ResourceSummaryTextState();
}

class _ResourceSummaryTextState extends State<ResourceSummaryText> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final summary = widget.summary?.trim();
    if (summary == null || summary.isEmpty) {
      return Text(
        '暂无摘要',
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          summary,
          maxLines: _expanded ? null : 2,
          overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
          style: theme.textTheme.bodyMedium,
        ),
        const SizedBox(height: 4),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            style: TextButton.styleFrom(
              visualDensity: VisualDensity.compact,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              minimumSize: const Size(48, 32),
            ),
            onPressed: () => setState(() => _expanded = !_expanded),
            child: Text(_expanded ? '收起' : '展开'),
          ),
        ),
        if (_expanded && widget.truncated)
          Text(
            '仅展示摘要前 N 字，查看完整内容请进入详情',
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
      ],
    );
  }
}
