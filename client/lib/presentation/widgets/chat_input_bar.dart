import 'package:flutter/material.dart';

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

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
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
              IconButton(
                icon: const Icon(Icons.send),
                tooltip: 'Send',
                onPressed: _send,
              ),
          ],
        ),
      ),
    );
  }
}
