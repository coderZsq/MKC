import 'package:flutter/material.dart';

/// Horizontally scrollable tag chips for a resource card.
class TagChipRow extends StatelessWidget {
  const TagChipRow({
    required this.tags,
    required this.onTagTap,
    super.key,
  });

  final List<String> tags;
  final ValueChanged<String> onTagTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (tags.isEmpty) {
      return Text(
        '暂无标签',
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
        ),
      );
    }

    return SizedBox(
      height: 36,
      child: Scrollbar(
        thumbVisibility: false,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: tags.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (context, index) {
            final tag = tags[index];
            return ActionChip(
              label: Text(tag, maxLines: 1, overflow: TextOverflow.ellipsis),
              visualDensity: VisualDensity.compact,
              onPressed: () => onTagTap(tag),
            );
          },
        ),
      ),
    );
  }
}
