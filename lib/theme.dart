import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ─── Color Palette ───
const Color kBgDark = Color(0xFF080C18);
const Color kBgMid = Color(0xFF0F1628);
const Color kBgLight = Color(0xFF1A2540);
const Color kCardBg = Color(0xFF1E2B45);
const Color kAccentGold = Color(0xFFFFCB47);
const Color kAccentPurple = Color(0xFF9B6DFF);
const Color kAccentBlue = Color(0xFF4DA8FF);
const Color kTextPrimary = Color(0xFFE8EAF6);
const Color kTextSecondary = Color(0xFF8896B3);

// Rarity colors
const Color kColorSSR = Color(0xFFFFD700);
const Color kColorSR = Color(0xFFCC88FF);
const Color kColorR = Color(0xFF66B2FF);

// Element colors
const Color kFireColor = Color(0xFFFF6B35);
const Color kWaterColor = Color(0xFF4ECDC4);
const Color kWindColor = Color(0xFF95E1D3);
const Color kEarthColor = Color(0xFFB8860B);
const Color kLightColor = Color(0xFFFFF9C4);
const Color kDarkColor = Color(0xFF9B59B6);

// HP bar colors
const Color kHpHigh = Color(0xFF4CAF50);
const Color kHpMid = Color(0xFFFFC107);
const Color kHpLow = Color(0xFFF44336);
const Color kUltGauge = Color(0xFF7C4DFF);

ThemeData buildAppTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: kBgDark,
    colorScheme: const ColorScheme.dark(
      primary: kAccentPurple,
      secondary: kAccentGold,
      surface: kBgMid,
      error: Color(0xFFFF5252),
    ),
    textTheme: GoogleFonts.notoSansTextTheme(
      ThemeData.dark().textTheme,
    ).copyWith(
      displayLarge: GoogleFonts.cinzelDecorative(
        color: kAccentGold,
        fontWeight: FontWeight.bold,
      ),
      titleLarge: GoogleFonts.cinzelDecorative(
        color: kTextPrimary,
        fontWeight: FontWeight.w600,
      ),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: kBgDark,
      elevation: 0,
      titleTextStyle: GoogleFonts.cinzelDecorative(
        color: kAccentGold,
        fontSize: 18,
        fontWeight: FontWeight.bold,
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: kBgMid,
      selectedItemColor: kAccentGold,
      unselectedItemColor: kTextSecondary,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kAccentPurple,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    ),
    cardTheme: CardThemeData(
      color: kCardBg,
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
  );
}

// ─── Rarity Gradient ───
LinearGradient rarityGradient(String rarity) {
  switch (rarity) {
    case 'SSR':
      return const LinearGradient(
        colors: [Color(0xFF7B4F00), Color(0xFFFFD700), Color(0xFFFFF0A0)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    case 'SR':
      return const LinearGradient(
        colors: [Color(0xFF3D1A6B), Color(0xFF9B6DFF), Color(0xFFD4AAFF)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    default:
      return const LinearGradient(
        colors: [Color(0xFF0D2137), Color(0xFF4DA8FF), Color(0xFFAAD4FF)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  }
}

Color rarityColor(String rarity) {
  switch (rarity) {
    case 'SSR':
      return kColorSSR;
    case 'SR':
      return kColorSR;
    default:
      return kColorR;
  }
}
