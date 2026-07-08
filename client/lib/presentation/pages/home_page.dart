import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../config/constants.dart';
import '../routes/app_routes.dart';

/// Placeholder home page.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(Constants.appName)),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.home_outlined, size: 64),
            const SizedBox(height: 16),
            const Text('首页占位 — 功能开发中'),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.push(uploadRoute),
              icon: const Icon(Icons.upload_file),
              label: const Text('上传文件'),
            ),
          ],
        ),
      ),
    );
  }
}
