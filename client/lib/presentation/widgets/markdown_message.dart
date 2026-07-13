import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../domain/entities/message.dart';
import '../../shared/validators.dart';
import 'citation_card.dart';

/// Renders assistant message content as Markdown and its citations.
class MarkdownMessage extends StatelessWidget {
  const MarkdownMessage({
    super.key,
    required this.message,
  });

  final Message message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (message.reasoning.isNotEmpty) ...<Widget>[
          ExpansionTile(
            title: Text(
              '思考过程',
              style: theme.textTheme.titleSmall,
            ),
            childrenPadding: const EdgeInsets.symmetric(horizontal: 16),
            children: <Widget>[
              SelectableText(
                message.reasoning,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
          const SizedBox(height: 8),
        ],
        MarkdownBody(
          data: message.content.isEmpty ? ' ' : message.content,
          selectable: true,
          styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(
            p: theme.textTheme.bodyMedium,
          ),
          onTapLink: (_, String? href, __) => _openLink(context, href),
        ),
        if (message.citations.isNotEmpty) ...<Widget>[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: message.citations
                .map((citation) => CitationCard(citation: citation))
                .toList(),
          ),
        ],
      ],
    );
  }

  Future<void> _openLink(BuildContext context, String? href) async {
    if (href == null || href.isEmpty) return;
    final uri = Uri.tryParse(href);
    if (uri == null ||
        uri.scheme.isEmpty ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      if (!context.mounted) return;
      _showWarning(context, 'Unsupported link');
      return;
    }
    if (!isValidResourceId(uri.host)) {
      if (!context.mounted) return;
      _showWarning(context, 'Unsupported link');
      return;
    }
    final canLaunch = await canLaunchUrl(uri);
    if (!context.mounted) return;
    if (!canLaunch) {
      _showWarning(context, 'Unable to open link');
      return;
    }
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  void _showWarning(BuildContext context, String text) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(text)),
    );
  }
}
