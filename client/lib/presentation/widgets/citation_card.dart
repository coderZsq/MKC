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
    final buffer = StringBuffer(citation.resourceName);
    if (citation.page != null && citation.page!.isNotEmpty) {
      buffer.write(' P${citation.page}');
    } else if (citation.timestamp != null) {
      final ts = citation.timestamp!;
      final minutes = ts.inMinutes.remainder(60).toString().padLeft(2, '0');
      final seconds = ts.inSeconds.remainder(60).toString().padLeft(2, '0');
      buffer.write(' ${ts.inHours.toString().padLeft(2, '0')}:$minutes:$seconds');
    }
    return buffer.toString();
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
    return ActionChip(
      avatar: const Icon(Icons.insert_drive_file_outlined, size: 18),
      label: Text(_label),
      onPressed: () => _onTap(context),
    );
  }
}
