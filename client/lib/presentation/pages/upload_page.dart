import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/upload_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/claude_layout.dart';
import '../widgets/upload_progress_bar.dart';

/// Page for selecting and uploading a file.
class UploadPage extends ConsumerWidget {
  const UploadPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(uploadNotifierProvider);
    final notifier = ref.read(uploadNotifierProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('上传文件')),
      body: ClaudePage(
        maxWidth: 720,
        children: [
          const ClaudeSectionHeader(
            label: 'Upload',
            title: '上传文件',
            description: '选择音频、PDF 或文档，进入解析与摘要流程。',
          ),
          const SizedBox(height: 24),
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildFileSelector(context, state, notifier),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('生成摘要'),
                value: state.autoSummary,
                onChanged: state.isUploading ? null : notifier.setAutoSummary,
              ),
              const SizedBox(height: 24),
              if (state.isUploading || state.progress > 0 && !state.isSuccess)
                UploadProgressBar(progress: state.progress),
              if (state.hasError) _buildError(context, state.errorMessage!),
              if (state.isSuccess)
                _buildSuccess(context, state.response!.taskId, notifier),
              if (state.isCancelled) _buildCancelled(context, notifier),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFileSelector(
    BuildContext context,
    UploadState state,
    UploadNotifier notifier,
  ) {
    final selected = state.selectedFile;

    return ClaudePanel(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (selected == null)
            const Text('请选择要上传的文件', textAlign: TextAlign.center)
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(selected.name,
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text('大小: ${_formatBytes(selected.size)}'),
                if (selected.extension != null)
                  Text('格式: ${selected.extension}'),
              ],
            ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton.icon(
                onPressed: state.isUploading ? null : notifier.pickFile,
                icon: const Icon(Icons.folder_open),
                label: Text(selected == null ? '选择文件' : '重新选择'),
              ),
              if (selected != null) ...[
                const SizedBox(width: 12),
                if (state.isUploading)
                  OutlinedButton.icon(
                    onPressed: notifier.cancel,
                    icon: const Icon(Icons.cancel),
                    label: const Text('取消'),
                  )
                else if (state.canUpload)
                  ElevatedButton.icon(
                    onPressed: notifier.upload,
                    icon: const Icon(Icons.upload_file),
                    label: const Text('开始上传'),
                  ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, String message) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Text(
        message,
        style: TextStyle(color: Theme.of(context).colorScheme.error),
        textAlign: TextAlign.center,
      ),
    );
  }

  Widget _buildSuccess(
      BuildContext context, String taskId, UploadNotifier notifier) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        children: [
          const Icon(Icons.check_circle, color: Colors.green, size: 48),
          const SizedBox(height: 8),
          const Text('上传成功', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('任务 ID: $taskId', textAlign: TextAlign.center),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: () {
              context.push(taskCenterRoute);
            },
            child: const Text('查看任务中心'),
          ),
          TextButton(
            onPressed: notifier.clear,
            child: const Text('继续上传'),
          ),
        ],
      ),
    );
  }

  Widget _buildCancelled(BuildContext context, UploadNotifier notifier) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        children: [
          const Text('上传已取消'),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: notifier.clear,
            child: const Text('重新选择'),
          ),
        ],
      ),
    );
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }
}
