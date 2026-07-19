import 'package:flutter/material.dart';

/// Application viewport breakpoints.
class AppBreakpoints {
  const AppBreakpoints({
    this.compact = 600,
    this.medium = 1024,
    this.expanded = 1440,
  });

  final double compact;
  final double medium;
  final double expanded;

  bool isCompact(double width) => width < compact;
  bool isMedium(double width) => width >= compact && width < medium;
  bool isExpanded(double width) => width >= medium;
}

const appBreakpoints = AppBreakpoints();

enum ResponsiveSizeClass {
  compact,
  medium,
  expanded,
}

ResponsiveSizeClass responsiveSizeClassForWidth(
  double width, {
  AppBreakpoints breakpoints = appBreakpoints,
}) {
  if (breakpoints.isCompact(width)) return ResponsiveSizeClass.compact;
  if (breakpoints.isMedium(width)) return ResponsiveSizeClass.medium;
  return ResponsiveSizeClass.expanded;
}

extension ResponsiveContext on BuildContext {
  double get viewportWidth => MediaQuery.sizeOf(this).width;

  ResponsiveSizeClass get sizeClass =>
      responsiveSizeClassForWidth(viewportWidth);

  bool get isCompactWidth => sizeClass == ResponsiveSizeClass.compact;
}

/// A small responsive shell for centered app pages.
class ResponsiveScaffold extends StatelessWidget {
  const ResponsiveScaffold({
    required this.child,
    this.compactPadding = const EdgeInsets.fromLTRB(12, 16, 12, 24),
    this.mediumPadding = const EdgeInsets.fromLTRB(20, 24, 20, 32),
    this.expandedPadding = const EdgeInsets.fromLTRB(24, 32, 24, 40),
    this.maxWidth = 1040,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry compactPadding;
  final EdgeInsetsGeometry mediumPadding;
  final EdgeInsetsGeometry expandedPadding;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final sizeClass = context.sizeClass;
    final padding = switch (sizeClass) {
      ResponsiveSizeClass.compact => compactPadding,
      ResponsiveSizeClass.medium => mediumPadding,
      ResponsiveSizeClass.expanded => expandedPadding,
    };

    return SafeArea(
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: Padding(
            padding: padding,
            child: child,
          ),
        ),
      ),
    );
  }
}
