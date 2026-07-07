import 'package:flutter/material.dart';

/// Application theme definitions.
abstract final class AppTheme {
  static const Color primaryColor = Color(0xFF6750A4);

  static ThemeData get light => ThemeData(
        colorSchemeSeed: primaryColor,
        useMaterial3: true,
        brightness: Brightness.light,
      );

  static ThemeData get dark => ThemeData(
        colorSchemeSeed: primaryColor,
        useMaterial3: true,
        brightness: Brightness.dark,
      );
}
