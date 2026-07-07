import 'package:flutter/material.dart';

import '../../config/constants.dart';

/// Launch screen shown while the app initializes.
class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 24),
            Text(
              Constants.appName,
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text(
              Constants.appSubtitle,
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}
