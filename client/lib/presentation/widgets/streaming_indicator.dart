import 'package:flutter/material.dart';

/// A simple loading indicator shown while the assistant is streaming.
class StreamingIndicator extends StatelessWidget {
  const StreamingIndicator({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'AI is thinking',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
