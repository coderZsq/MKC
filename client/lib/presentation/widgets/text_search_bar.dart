import 'package:flutter/material.dart';

/// Search bar for content view with prev/next navigation.
class TextSearchBar extends StatelessWidget {
  const TextSearchBar({
    required this.keyword,
    required this.matchCount,
    required this.currentIndex,
    required this.onChanged,
    required this.onPrevious,
    required this.onNext,
    super.key,
  });

  final String keyword;
  final int matchCount;
  final int currentIndex;
  final ValueChanged<String> onChanged;
  final VoidCallback onPrevious;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              key: const Key('content_search_field'),
              decoration: const InputDecoration(
                hintText: '搜索内容',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(vertical: 8),
              ),
              onChanged: onChanged,
            ),
          ),
          if (keyword.isNotEmpty) ...[
            const SizedBox(width: 8),
            Text(
              matchCount == 0
                  ? '无结果'
                  : '${currentIndex + 1} / $matchCount',
              key: const Key('content_search_count'),
            ),
            IconButton(
              key: const Key('content_search_previous'),
              icon: const Icon(Icons.keyboard_arrow_up),
              onPressed: matchCount == 0 ? null : onPrevious,
            ),
            IconButton(
              key: const Key('content_search_next'),
              icon: const Icon(Icons.keyboard_arrow_down),
              onPressed: matchCount == 0 ? null : onNext,
            ),
          ],
        ],
      ),
    );
  }
}
