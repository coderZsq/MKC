import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../config/theme.dart';
import '../providers/conversation_list_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/claude_layout.dart';
import '../widgets/error_banner.dart';

/// Lists conversations and lets the user start or delete one.
class ConversationListPage extends ConsumerWidget {
  const ConversationListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(conversationListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Conversations'),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'New conversation',
            onPressed: () => _createAndOpen(context, ref),
          ),
        ],
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 16),
            child: ClaudeSectionHeader(
              label: 'Chat',
              title: 'Conversations',
              description: '继续已有对话，或创建一个新的资源问答会话。',
              action: FilledButton.icon(
                onPressed: () => _createAndOpen(context, ref),
                icon: const Icon(Icons.add),
                label: const Text('New'),
              ),
            ),
          ),
          if (state.error != null)
            ErrorBanner(
              message: state.error!.message,
              onDismiss: () =>
                  ref.read(conversationListProvider.notifier).clearError(),
            ),
          Expanded(
            child: _buildBody(context, ref, state),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    ConversationListState state,
  ) {
    if (state.isLoading && state.conversations.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.conversations.isEmpty) {
      return ClaudeEmptyState(
        title: 'No conversations yet',
        icon: Icons.forum_outlined,
        action: ElevatedButton.icon(
          onPressed: () => _createAndOpen(context, ref),
          icon: const Icon(Icons.add),
          label: const Text('Start a new conversation'),
        ),
      );
    }

    return ClaudeListShell(
      padding: EdgeInsets.zero,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
        itemCount: state.conversations.length,
        itemBuilder: (context, index) {
          final conversation = state.conversations[index];
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: ClaudePanel(
              padding: EdgeInsets.zero,
              child: ListTile(
                title: Text(
                  conversation.title.isEmpty
                      ? 'Untitled conversation'
                      : conversation.title,
                ),
                subtitle: Text(
                  'Updated ${DateFormat.yMd().add_Hm().format(conversation.updatedAt)}',
                ),
                leading: const Icon(Icons.chat_bubble_outline),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline),
                  tooltip: 'Delete',
                  onPressed: () => _delete(context, ref, conversation.id),
                ),
                onTap: () => _openConversation(context, conversation.id),
              ),
            ),
          );
        },
      ),
    );
  }

  Future<void> _createAndOpen(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(conversationListProvider.notifier);
    final conversation = await notifier.createConversation();
    if (conversation == null) return;
    if (!context.mounted) return;
    _openConversation(context, conversation.id);
  }

  void _openConversation(BuildContext context, String id) {
    context.push(conversationRoute.replaceFirst(':id', id));
  }

  void _delete(BuildContext context, WidgetRef ref, String id) {
    final theme = Theme.of(context);
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: ClaudeColors.ivory,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        titleTextStyle: theme.textTheme.headlineSmall,
        contentTextStyle: theme.textTheme.bodyMedium,
        title: const Text('Delete conversation'),
        content:
            const Text('Are you sure you want to delete this conversation?'),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              ref
                  .read(conversationListProvider.notifier)
                  .deleteConversation(id);
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}
