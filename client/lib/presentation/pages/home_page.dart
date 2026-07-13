import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../config/constants.dart';
import '../routes/app_routes.dart';

/// Home page with quick debug entry points for major flows.
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _taskIdController = TextEditingController();
  final TextEditingController _conversationIdController =
      TextEditingController();

  @override
  void dispose() {
    _taskIdController.dispose();
    _conversationIdController.dispose();
    super.dispose();
  }

  void _openTaskDetail() {
    final taskId = _taskIdController.text.trim();
    if (taskId.isEmpty) return;
    context.push(taskDetailRoute.replaceFirst(':id', taskId));
  }

  void _openTaskContent(String type) {
    final taskId = _taskIdController.text.trim();
    if (taskId.isEmpty) return;
    final path = contentViewRoute.replaceFirst(':id', taskId);
    context.push('$path?type=$type');
  }

  void _openConversation() {
    final conversationId = _conversationIdController.text.trim();
    if (conversationId.isEmpty) return;
    context.push(conversationRoute.replaceFirst(':id', conversationId));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text(Constants.appName)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              '首页占位 — 功能开发中',
              style: theme.textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            Text(
              '调试入口',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '常用页面和需要 ID 的链路集中在这里。',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),
            _EntryGrid(
              entries: [
                _DebugEntry(
                  title: '上传文件',
                  subtitle: '文件选择与上传',
                  icon: Icons.upload_file,
                  onTap: () => context.push(uploadRoute),
                ),
                _DebugEntry(
                  title: '任务中心',
                  subtitle: '任务列表与状态',
                  icon: Icons.task_alt,
                  onTap: () => context.push(taskCenterRoute),
                ),
                _DebugEntry(
                  title: '资源库',
                  subtitle: '摘要与标签',
                  icon: Icons.folder_copy_outlined,
                  onTap: () => context.push(resourcesRoute),
                ),
                _DebugEntry(
                  title: '会话列表',
                  subtitle: '创建与管理会话',
                  icon: Icons.forum_outlined,
                  onTap: () => context.push(conversationListRoute),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _DebugPanel(
              title: '任务调试',
              icon: Icons.manage_search,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _taskIdController,
                    decoration: const InputDecoration(
                      labelText: 'Task ID',
                      prefixIcon: Icon(Icons.tag),
                      border: OutlineInputBorder(),
                    ),
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _openTaskDetail(),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      FilledButton.icon(
                        onPressed: _openTaskDetail,
                        icon: const Icon(Icons.open_in_new),
                        label: const Text('任务详情'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _openTaskContent('audio'),
                        icon: const Icon(Icons.subtitles_outlined),
                        label: const Text('音频内容'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _openTaskContent('pdf'),
                        icon: const Icon(Icons.picture_as_pdf_outlined),
                        label: const Text('PDF 内容'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _DebugPanel(
              title: '会话调试',
              icon: Icons.chat_bubble_outline,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _conversationIdController,
                    decoration: const InputDecoration(
                      labelText: 'Conversation ID',
                      prefixIcon: Icon(Icons.tag),
                      border: OutlineInputBorder(),
                    ),
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _openConversation(),
                  ),
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: FilledButton.icon(
                      onPressed: _openConversation,
                      icon: const Icon(Icons.open_in_new),
                      label: const Text('打开会话'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EntryGrid extends StatelessWidget {
  const _EntryGrid({required this.entries});

  final List<_DebugEntry> entries;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 720 ? 3 : 1;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: entries.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: columns == 1 ? 4.2 : 2.6,
          ),
          itemBuilder: (context, index) => _EntryCard(entry: entries[index]),
        );
      },
    );
  }
}

class _EntryCard extends StatelessWidget {
  const _EntryCard({required this.entry});

  final _DebugEntry entry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      clipBehavior: Clip.antiAlias,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: InkWell(
        onTap: entry.onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(entry.icon, size: 28, color: theme.colorScheme.primary),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      entry.subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}

class _DebugPanel extends StatelessWidget {
  const _DebugPanel({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            child,
          ],
        ),
      ),
    );
  }
}

class _DebugEntry {
  const _DebugEntry({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;
}
