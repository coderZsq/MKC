import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../domain/entities/message.dart';

import '../../shared/validators.dart';

/// A clickable chip that navigates to the cited resource.
class CitationCard extends StatelessWidget {
  const CitationCard({
    super.key,
    required this.citation,
  });

  final Citation citation;

  String get _label {
    final buffer = StringBuffer();
    if (citation.index != null) {
      buffer.write('[^${citation.index}] ');
    }
    buffer.write(citation.resourceName);
    if (citation.page != null && citation.page!.isNotEmpty) {
      buffer.write(' 第 ${citation.page} 页');
    } else if (citation.timestamp != null) {
      buffer.write(' ${_formatTimestamp(citation.timestamp!)}');
      if (citation.timestampEnd != null) {
        buffer.write('-${_formatTimestamp(citation.timestampEnd!)}');
      }
    }
    return buffer.toString();
  }

  String _formatTimestamp(Duration duration) {
    final totalSeconds = duration.inSeconds;
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _onTap(BuildContext context) {
    if (!isValidResourceId(citation.resourceId)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid citation resource ID')),
      );
      return;
    }
    context.go(
      '/tasks/${citation.resourceId}/content?type=${citation.contentType.paramValue}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final snippet = citation.snippet;
    return Tooltip(
      message: snippet == null || snippet.isEmpty ? _label : snippet,
      child: ActionChip(
        avatar: const Icon(Icons.insert_drive_file_outlined, size: 18),
        label: Text(_label),
        onPressed: () => _onTap(context),
      ),
    );
  }
}
