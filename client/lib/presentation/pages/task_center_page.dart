import 'package:flutter/material.dart';

/// Placeholder task center page.
class TaskCenterPage extends StatelessWidget {
  const TaskCenterPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('任务中心')),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.list_alt_outlined, size: 64),
            SizedBox(height: 16),
            Text('任务中心占位 — 功能开发中'),
          ],
        ),
      ),
    );
  }
}
