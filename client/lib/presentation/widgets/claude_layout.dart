import 'package:flutter/material.dart';

import '../../config/theme.dart';

class ClaudePage extends StatelessWidget {
  const ClaudePage({
    required this.children,
    this.padding = const EdgeInsets.fromLTRB(24, 32, 24, 40),
    this.maxWidth = 1040,
    this.physics,
    super.key,
  });

  final List<Widget> children;
  final EdgeInsetsGeometry padding;
  final double maxWidth;
  final ScrollPhysics? physics;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: ListView(
            physics: physics,
            padding: padding,
            children: children,
          ),
        ),
      ),
    );
  }
}

class ClaudeSectionHeader extends StatelessWidget {
  const ClaudeSectionHeader({
    required this.label,
    required this.title,
    this.description,
    this.action,
    super.key,
  });

  final String label;
  final String title;
  final String? description;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClaudeEyebrow(label),
              const SizedBox(height: 10),
              Text(title, style: theme.textTheme.headlineLarge),
              if (description != null) ...[
                const SizedBox(height: 10),
                Text(
                  description!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: ClaudeColors.oliveGray,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (action != null) ...[
          const SizedBox(width: 16),
          action!,
        ],
      ],
    );
  }
}

class ClaudeEyebrow extends StatelessWidget {
  const ClaudeEyebrow(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: ClaudeColors.terracotta,
            fontFamily: ClaudeFonts.sans,
            fontFamilyFallback: ClaudeFonts.sansFallback,
            fontWeight: FontWeight.w600,
            letterSpacing: 2.5,
          ),
    );
  }
}

class ClaudePanel extends StatelessWidget {
  const ClaudePanel({
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.margin = EdgeInsets.zero,
    this.onTap,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final paddedChild = Padding(padding: padding, child: child);
    final panelChild = onTap == null
        ? paddedChild
        : Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(8),
              child: paddedChild,
            ),
          );
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: ClaudeColors.ivory,
        border: Border.all(color: ClaudeColors.borderCream),
        borderRadius: BorderRadius.circular(8),
      ),
      child: panelChild,
    );
  }
}

class ClaudeEmptyState extends StatelessWidget {
  const ClaudeEmptyState({
    required this.title,
    this.message,
    this.icon = Icons.inbox_outlined,
    this.action,
    super.key,
  });

  final String title;
  final String? message;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: ClaudePanel(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: ClaudeColors.warmSand,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: ClaudeColors.ringWarm),
                ),
                child: Icon(icon, color: ClaudeColors.terracotta),
              ),
              const SizedBox(height: 16),
              Text(
                title,
                textAlign: TextAlign.center,
                style: theme.textTheme.titleLarge,
              ),
              if (message != null) ...[
                const SizedBox(height: 8),
                Text(
                  message!,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: ClaudeColors.oliveGray,
                  ),
                ),
              ],
              if (action != null) ...[
                const SizedBox(height: 20),
                action!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class ClaudeListShell extends StatelessWidget {
  const ClaudeListShell({
    required this.child,
    this.padding = const EdgeInsets.fromLTRB(16, 14, 16, 28),
    this.maxWidth = 960,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Padding(
          padding: padding,
          child: child,
        ),
      ),
    );
  }
}
