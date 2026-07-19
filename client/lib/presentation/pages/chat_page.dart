import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/responsive/breakpoints.dart';
import '../providers/chat_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/chat_input_bar.dart';
import '../widgets/claude_layout.dart';
import '../widgets/streaming_indicator.dart';
import '../../shared/validators.dart';

/// Chat screen for a single conversation.
class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({
    super.key,
    required this.conversationId,
  });

  final String conversationId;

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    if (!isValidResourceId(widget.conversationId)) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Invalid conversation ID')),
          );
        }
      });
    }
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent,
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!isValidResourceId(widget.conversationId)) {
      return Scaffold(
        appBar: AppBar(title: const Text('Chat')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text('Invalid conversation ID', textAlign: TextAlign.center),
          ),
        ),
      );
    }

    final state = ref.watch(chatProvider(widget.conversationId));

    ref.listen<ChatState>(
      chatProvider(widget.conversationId),
      (_, next) {
        if (!next.isSending) {
          WidgetsBinding.instance
              .addPostFrameCallback((_) => _scrollToBottom());
        }
      },
    );

    final title = state.title.isEmpty ? 'Chat' : state.title;

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.list),
            tooltip: 'Conversations',
            onPressed: () => _openConversationList(context),
          ),
        ],
      ),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: Column(
            children: <Widget>[
              Expanded(
                child: _buildMessageList(state),
              ),
              if (state.error != null && state.messages.isNotEmpty)
                _StreamErrorRetryBar(
                  message: state.error!.message,
                  canRetry: state.canRetryLastQuestion,
                  onRetry: () => ref
                      .read(chatProvider(widget.conversationId).notifier)
                      .retryLastQuestion(),
                  onDismiss: () => ref
                      .read(chatProvider(widget.conversationId).notifier)
                      .clearError(),
                ),
              ChatInputBar(
                enabled: !state.isSending,
                onSend: (question) => _send(question),
                onCancel: () => _cancel(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessageList(ChatState state) {
    if (state.isLoading && state.messages.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.messages.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            state.error!.message,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    if (state.messages.isEmpty) {
      return const ClaudeEmptyState(
        title: 'Send a message to start the conversation',
        message: 'Ask a question about your uploaded resources.',
        icon: Icons.chat_bubble_outline,
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: EdgeInsets.fromLTRB(
        context.isCompactWidth ? 8 : 12,
        16,
        context.isCompactWidth ? 8 : 12,
        20,
      ),
      itemCount: state.messages.length + (state.isSending ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == state.messages.length) {
          return const Padding(
            padding: EdgeInsets.only(left: 16, top: 8),
            child: StreamingIndicator(),
          );
        }
        return ChatBubble(message: state.messages[index]);
      },
    );
  }

  void _send(String question) {
    ref.read(chatProvider(widget.conversationId).notifier).send(question);
  }

  void _cancel() {
    ref.read(chatProvider(widget.conversationId).notifier).cancel();
  }

  void _openConversationList(BuildContext context) {
    context.push(conversationListRoute);
  }
}

class _StreamErrorRetryBar extends StatelessWidget {
  const _StreamErrorRetryBar({
    required this.message,
    required this.canRetry,
    required this.onRetry,
    required this.onDismiss,
  });

  final String message;
  final bool canRetry;
  final VoidCallback onRetry;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final isCompact = context.isCompactWidth;
    final content = <Widget>[
      Icon(
        Icons.wifi_off_outlined,
        color: Theme.of(context).colorScheme.error,
        size: 20,
      ),
      Expanded(child: Text(message)),
      if (canRetry)
        TextButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: const Text('重试'),
        ),
      IconButton(
        onPressed: onDismiss,
        icon: const Icon(Icons.close),
        tooltip: '关闭',
      ),
    ];

    return SafeArea(
      top: false,
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.fromLTRB(
          isCompact ? 8 : 12,
          8,
          isCompact ? 8 : 12,
          8,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.errorContainer,
          border: Border(
            top:
                BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
          ),
        ),
        child: Row(children: content),
      ),
    );
  }
}
