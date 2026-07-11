import 'package:flutter/material.dart';

/// A dismissible banner that shows an error message.
class ErrorBanner extends StatelessWidget {
  const ErrorBanner({
    super.key,
    required this.message,
    this.onDismiss,
  });

  final String message;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    return MaterialBanner(
      content: Text(message),
      actions: <Widget>[
        TextButton(
          onPressed: onDismiss,
          child: const Text('DISMISS'),
        ),
      ],
    );
  }
}
