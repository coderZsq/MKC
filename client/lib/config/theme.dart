import 'package:flutter/material.dart';

/// Application theme definitions.
abstract final class AppTheme {
  static const Color primaryColor = ClaudeColors.terracotta;

  static ThemeData get light {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: primaryColor,
      brightness: Brightness.light,
      surface: ClaudeColors.ivory,
      onSurface: ClaudeColors.nearBlack,
      primary: ClaudeColors.terracotta,
      onPrimary: ClaudeColors.ivory,
      primaryContainer: ClaudeColors.warmSand,
      onPrimaryContainer: ClaudeColors.nearBlack,
      secondary: ClaudeColors.charcoalWarm,
      onSecondary: ClaudeColors.ivory,
      secondaryContainer: ClaudeColors.warmSand,
      onSecondaryContainer: ClaudeColors.darkWarm,
      error: ClaudeColors.error,
      outline: ClaudeColors.ringWarm,
      outlineVariant: ClaudeColors.borderWarm,
      surfaceContainerLowest: ClaudeColors.white,
      surfaceContainerLow: ClaudeColors.ivory,
      surfaceContainer: ClaudeColors.parchment,
      surfaceContainerHigh: ClaudeColors.borderCream,
      surfaceContainerHighest: ClaudeColors.warmSand,
    );

    final textTheme = _textTheme(ClaudeColors.nearBlack);

    return ThemeData(
      colorScheme: colorScheme,
      scaffoldBackgroundColor: ClaudeColors.parchment,
      canvasColor: ClaudeColors.parchment,
      cardColor: ClaudeColors.ivory,
      dividerColor: ClaudeColors.borderCream,
      useMaterial3: true,
      brightness: Brightness.light,
      fontFamily: ClaudeFonts.sans,
      fontFamilyFallback: ClaudeFonts.sansFallback,
      textTheme: textTheme,
      primaryTextTheme: textTheme,
      appBarTheme: AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        backgroundColor: ClaudeColors.parchment.withAlpha(235),
        foregroundColor: ClaudeColors.nearBlack,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          fontFamily: ClaudeFonts.serif,
          fontFamilyFallback: ClaudeFonts.serifFallback,
          fontWeight: FontWeight.w500,
          color: ClaudeColors.nearBlack,
        ),
        iconTheme: const IconThemeData(color: ClaudeColors.charcoalWarm),
        actionsIconTheme: const IconThemeData(color: ClaudeColors.charcoalWarm),
        shape: const Border(
          bottom: BorderSide(color: ClaudeColors.borderCream),
        ),
      ),
      listTileTheme: ListTileThemeData(
        iconColor: ClaudeColors.terracotta,
        textColor: ClaudeColors.nearBlack,
        subtitleTextStyle: textTheme.bodySmall?.copyWith(
          color: ClaudeColors.oliveGray,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: _brandButtonStyle(colorScheme),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: _brandButtonStyle(colorScheme),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ClaudeColors.charcoalWarm,
          backgroundColor: ClaudeColors.warmSand,
          side: const BorderSide(color: ClaudeColors.ringWarm),
          elevation: 0,
          minimumSize: const Size(48, 44),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle:
              textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w500),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: ClaudeColors.terracotta,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          textStyle:
              textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w500),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: ClaudeColors.charcoalWarm,
          hoverColor: ClaudeColors.warmSand,
          focusColor: ClaudeColors.warmSand,
          highlightColor: ClaudeColors.warmSand,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: ClaudeColors.ivory,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        prefixIconColor: ClaudeColors.stoneGray,
        labelStyle:
            textTheme.bodyMedium?.copyWith(color: ClaudeColors.oliveGray),
        hintStyle:
            textTheme.bodyMedium?.copyWith(color: ClaudeColors.stoneGray),
        enabledBorder: _inputBorder(ClaudeColors.borderWarm),
        focusedBorder: _inputBorder(ClaudeColors.terracotta, width: 1.4),
        errorBorder: _inputBorder(ClaudeColors.error),
        focusedErrorBorder: _inputBorder(ClaudeColors.error, width: 1.4),
        border: _inputBorder(ClaudeColors.borderWarm),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: ClaudeColors.warmSand,
        selectedColor: ClaudeColors.terracotta.withAlpha(36),
        disabledColor: ClaudeColors.borderCream,
        side: const BorderSide(color: ClaudeColors.ringWarm),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        labelStyle: textTheme.labelMedium?.copyWith(
          color: ClaudeColors.charcoalWarm,
          fontWeight: FontWeight.w500,
        ),
        secondaryLabelStyle: textTheme.labelMedium?.copyWith(
          color: ClaudeColors.ivory,
          fontWeight: FontWeight.w500,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: ClaudeColors.darkSurface,
        contentTextStyle:
            textTheme.bodyMedium?.copyWith(color: ClaudeColors.ivory),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? ClaudeColors.ivory
              : ClaudeColors.stoneGray,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? ClaudeColors.terracotta
              : ClaudeColors.warmSand,
        ),
        trackOutlineColor: WidgetStateProperty.all(ClaudeColors.ringWarm),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: ClaudeColors.terracotta,
        linearTrackColor: ClaudeColors.warmSand,
        circularTrackColor: ClaudeColors.warmSand,
      ),
      dividerTheme: const DividerThemeData(
        color: ClaudeColors.borderCream,
        thickness: 1,
        space: 1,
      ),
      expansionTileTheme: const ExpansionTileThemeData(
        backgroundColor: ClaudeColors.ivory,
        collapsedBackgroundColor: ClaudeColors.ivory,
        iconColor: ClaudeColors.charcoalWarm,
        collapsedIconColor: ClaudeColors.charcoalWarm,
        textColor: ClaudeColors.nearBlack,
        collapsedTextColor: ClaudeColors.nearBlack,
      ),
    );
  }

  static ThemeData get dark => light;

  static ButtonStyle _brandButtonStyle(ColorScheme colorScheme) {
    return FilledButton.styleFrom(
      foregroundColor: ClaudeColors.ivory,
      backgroundColor: ClaudeColors.terracotta,
      disabledForegroundColor: ClaudeColors.stoneGray,
      disabledBackgroundColor: ClaudeColors.warmSand,
      elevation: 0,
      minimumSize: const Size(48, 44),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      textStyle: _textTheme(ClaudeColors.nearBlack).labelLarge?.copyWith(
            fontWeight: FontWeight.w500,
          ),
    );
  }

  static OutlineInputBorder _inputBorder(Color color, {double width = 1}) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: BorderSide(color: color, width: width),
    );
  }

  static TextTheme _textTheme(Color color) {
    const serif = ClaudeFonts.serif;
    const sans = ClaudeFonts.sans;
    const mono = ClaudeFonts.mono;
    const serifFallback = ClaudeFonts.serifFallback;
    const sansFallback = ClaudeFonts.sansFallback;
    const monoFallback = ClaudeFonts.monoFallback;

    return TextTheme(
      displayLarge: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 64,
        height: 1.1,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      displayMedium: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 44,
        height: 1.16,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      headlineLarge: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 36,
        height: 1.2,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      headlineMedium: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 30,
        height: 1.22,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      headlineSmall: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 24,
        height: 1.25,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      titleLarge: TextStyle(
        fontFamily: serif,
        fontFamilyFallback: serifFallback,
        fontSize: 20,
        height: 1.25,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      titleMedium: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 16,
        height: 1.35,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      titleSmall: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 14,
        height: 1.35,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      bodyLarge: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 18,
        height: 1.6,
        fontWeight: FontWeight.w400,
        color: color,
      ),
      bodyMedium: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 16,
        height: 1.6,
        fontWeight: FontWeight.w400,
        color: color,
      ),
      bodySmall: const TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 13,
        height: 1.45,
        fontWeight: FontWeight.w400,
        color: ClaudeColors.oliveGray,
      ),
      labelLarge: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 15,
        height: 1.2,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      labelMedium: TextStyle(
        fontFamily: sans,
        fontFamilyFallback: sansFallback,
        fontSize: 13,
        height: 1.2,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      labelSmall: const TextStyle(
        fontFamily: mono,
        fontFamilyFallback: monoFallback,
        fontSize: 12,
        height: 1.35,
        fontWeight: FontWeight.w500,
        color: ClaudeColors.stoneGray,
      ),
    );
  }
}

abstract final class ClaudeColors {
  static const Color nearBlack = Color(0xFF141413);
  static const Color terracotta = Color(0xFFC96442);
  static const Color coral = Color(0xFFD97757);
  static const Color error = Color(0xFFB53333);
  static const Color focusBlue = Color(0xFF3898EC);
  static const Color parchment = Color(0xFFF5F4ED);
  static const Color ivory = Color(0xFFFAF9F5);
  static const Color white = Color(0xFFFFFFFF);
  static const Color warmSand = Color(0xFFE8E6DC);
  static const Color darkSurface = Color(0xFF30302E);
  static const Color charcoalWarm = Color(0xFF4D4C48);
  static const Color oliveGray = Color(0xFF5E5D59);
  static const Color stoneGray = Color(0xFF87867F);
  static const Color darkWarm = Color(0xFF3D3D3A);
  static const Color warmSilver = Color(0xFFB0AEA5);
  static const Color borderCream = Color(0xFFF0EEE6);
  static const Color borderWarm = Color(0xFFE8E6DC);
  static const Color ringWarm = Color(0xFFD1CFC5);
  static const Color ringDeep = Color(0xFFC2C0B6);
}

abstract final class ClaudeFonts {
  static const String serif = 'Georgia';
  static const String sans = 'Arial';
  static const String mono = 'SFMono-Regular';

  static const List<String> serifFallback = [
    'Times New Roman',
    'Songti SC',
    'serif',
  ];
  static const List<String> sansFallback = [
    'system-ui',
    'PingFang SC',
    'Microsoft YaHei',
    'sans-serif',
  ];
  static const List<String> monoFallback = [
    'Menlo',
    'Monaco',
    'Consolas',
    'monospace',
  ];
}
