import 'package:flutter/material.dart';
import '../theme.dart';

class StatBar extends StatelessWidget {
  final int current;
  final int max;
  final double height;
  final bool showText;
  final String? label;

  const StatBar({
    super.key,
    required this.current,
    required this.max,
    this.height = 8,
    this.showText = false,
    this.label,
  });

  Color get _barColor {
    final ratio = max == 0 ? 0.0 : current / max;
    if (ratio > 0.5) return kHpHigh;
    if (ratio > 0.25) return kHpMid;
    return kHpLow;
  }

  @override
  Widget build(BuildContext context) {
    final ratio = max == 0 ? 0.0 : (current / max).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (label != null || showText)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (label != null)
                Text(label!, style: const TextStyle(color: kTextSecondary, fontSize: 11)),
              if (showText)
                Text(
                  '$current / $max',
                  style: const TextStyle(color: kTextPrimary, fontSize: 11),
                ),
            ],
          ),
        if (label != null || showText) const SizedBox(height: 2),
        ClipRRect(
          borderRadius: BorderRadius.circular(height / 2),
          child: LinearProgressIndicator(
            value: ratio,
            minHeight: height,
            backgroundColor: Colors.white12,
            valueColor: AlwaysStoppedAnimation<Color>(_barColor),
          ),
        ),
      ],
    );
  }
}

class UltGaugeBar extends StatelessWidget {
  final int gauge; // 0-100
  final double height;

  const UltGaugeBar({super.key, required this.gauge, this.height = 6});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(height / 2),
      child: LinearProgressIndicator(
        value: gauge / 100,
        minHeight: height,
        backgroundColor: Colors.white12,
        valueColor: const AlwaysStoppedAnimation<Color>(kUltGauge),
      ),
    );
  }
}
