import 'package:flutter/material.dart';

import '../../config/theme.dart';
import '../../domain/entities/message.dart';
import 'markdown_message.dart';

/// Displays a single chat message for the user or the assistant.
class ChatBubble extends StatelessWidget {
  const ChatBubble({
    super.key,
    required this.message,
  });

  final Message message;

  bool get _isUser => message.role == MessageRole.user;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final alignment = _isUser ? Alignment.centerRight : Alignment.centerLeft;
    final bubbleColor = _isUser ? ClaudeColors.terracotta : ClaudeColors.ivory;
    final textColor = _isUser ? ClaudeColors.ivory : ClaudeColors.nearBlack;

    return Align(
      alignment: alignment,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: bubbleColor,
            border: Border.all(
              color:
                  _isUser ? ClaudeColors.terracotta : ClaudeColors.borderCream,
            ),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(12),
              topRight: const Radius.circular(12),
              bottomLeft: Radius.circular(_isUser ? 12 : 6),
              bottomRight: Radius.circular(_isUser ? 6 : 12),
            ),
          ),
          child: _isUser
              ? Text(
                  message.content,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: textColor,
                  ),
                )
              : MarkdownMessage(message: message),
        ),
      ),
    );
  }
}
