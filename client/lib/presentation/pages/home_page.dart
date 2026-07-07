import 'package:flutter/material.dart';

import '../../config/constants.dart';

/// Placeholder home page.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(Constants.appName)),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.home_outlined, size: 64),
            SizedBox(height: 16),
            Text('首页占位 — 功能开发中'),
          ],
        ),
      ),
    );
  }
}
