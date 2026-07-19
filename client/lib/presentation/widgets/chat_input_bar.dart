import 'package:flutter/material.dart';

import '../../core/responsive/breakpoints.dart';
import '../../config/theme.dart';

const int _maxQuestionLength = 2000;

/// Bottom input bar with send and cancel actions.
class ChatInputBar extends StatefulWidget {
  const ChatInputBar({
    super.key,
    required this.onSend,
    required this.enabled,
    this.onCancel,
  });

  final ValueChanged<String> onSend;
  final VoidCallback? onCancel;
  final bool enabled;

  @override
  State<ChatInputBar> createState() => _ChatInputBarState();
}

class _ChatInputBarState extends State<ChatInputBar> {
  final _controller = TextEditingController();

  void _send() {
    final text = _controller.text.trim();
    if (text.isEmpty || !widget.enabled) return;
    widget.onSend(text);
    _controller.clear();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isSending = !widget.enabled;
    final isCompact = context.isCompactWidth;

    return SafeArea(
      child: Container(
        padding: EdgeInsets.fromLTRB(
          isCompact ? 8 : 12,
          10,
          isCompact ? 8 : 12,
          12,
        ),
        decoration: BoxDecoration(
          color: ClaudeColors.parchment.withAlpha(242),
          border: Border(
            top: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: TextField(
                controller: _controller,
                enabled: widget.enabled,
                textInputAction: TextInputAction.send,
                maxLines: null,
                minLines: 1,
                scrollPadding: EdgeInsets.only(
                  bottom: MediaQuery.viewInsetsOf(context).bottom + 96,
                ),
                maxLength: _maxQuestionLength,
                decoration: const InputDecoration(
                  hintText: 'Type a question',
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                ),
                onSubmitted: (_) => _send(),
              ),
            ),
            const SizedBox(width: 8),
            if (isSending)
              IconButton(
                icon: const Icon(Icons.stop),
                tooltip: 'Cancel',
                onPressed: widget.onCancel,
              )
            else
              FilledButton(
                style: FilledButton.styleFrom(
                  minimumSize: const Size(44, 44),
                  padding: EdgeInsets.zero,
                ),
                onPressed: _send,
                child: const Icon(Icons.send, size: 20),
              ),
          ],
        ),
      ),
    );
  }
}
