# Ergebnis: 6 Strategien x 30 Märkte auf M1 (Offline-Test)

**Kurz: Keine der 6 Strategien funktioniert auf M1, in keinem der 30 Märkte.**
0 von 95 Kombinationen mit genug Trades sind schon im Lernzeitraum signifikant positiv
(per Zufall wären ~2 zu erwarten). Alle 6 Strategien verlieren über alle Märkte, in beiden Zeiträumen.
44.705 Trades, im Schnitt -0,10 R pro Trade.

## Warum: Die Kosten fressen den Vorteil 4-5-fach

Gleiche Trades, einmal ohne Kosten, mit halbem Spread und mit vollen Kosten (Ø R pro Trade):

| Strategie | Trades | vor Kosten | halber Spread | volle Kosten |
|---|---|---|---|---|
| ORB | 7.600 | +0,018 | -0,051 | -0,087 |
| ASIA_MR | 2.838 | +0,006 | -0,059 | -0,110 |
| SQUEEZE | 1.353 | -0,065 | -0,142 | -0,185 |
| TWAP_MR | 21.091 | +0,024 | -0,041 | -0,086 |
| MOMO | 11.782 | -0,008 | -0,081 | -0,116 |
| FIX_FADE | 41 | -0,102 | -0,132 | -0,162 |

- Vor Kosten liegen alle Strategien bei ungefähr 0 R. Den größten Rohvorteil hat TWAP_MR mit +0,024 R pro Trade.
- Spread und Kommission kosten auf M1 rund 0,1 R pro Trade, obwohl Trades mit Kosten > 20 % des Risikos
  schon aussortiert werden (das betraf ~560.000 Signale).
- Selbst mit halbem Spread (enger als bei jedem Retail-Broker realistisch) bleibt alles negativ.

**Folgerung:** Auf M1 braucht eine Strategie einen Rohvorteil von > 0,1 R pro Trade, nur um die Kosten
zu decken. Je kleiner der Zeitrahmen, desto kleiner der Stop und desto größer der Kostenanteil.
Auf M15/H1 machen dieselben Kosten nur noch ~2-5 % des Risikos aus.

## Datenbasis und Grenzen
- Kurse: HistData M1 (Bid), Okt 2025 - Sep 2026, ~10,5 Mio. Kerzen. Lernzeitraum bis 31.05.2026,
  Prüfzeitraum Jun-Sep 2026. WTI nur teilweise verfügbar.
- Spreads: gemessen aus Dukascopy-Bid/Ask (1-2 Tage je Markt, je UTC-Stunde), für USDCAD/AUDJPY
  Annahmen. Für Kreuzpaare und Gold vermutlich weiter als bei Fusion Zero, daher die Spalte "halber Spread".
- Kommission: 4,50 USD/Lot (FX, Metalle), Indizes/Öl nur Spread.
- Parameter vorab festgelegt, nichts auf die Daten optimiert.
- Die endgültige Prüfung mit echten Fusion-Daten: `python -m research.run --source mt5 --days 365` auf dem PC.

## Vollständiger Bericht

- Märkte: 30, Strategien: 6, Kombinationen mit genug Trades: 95
- Lernzeitraum (IS) bis 2026-06-01, Prüfzeitraum (OOS) danach
- Ergebnis in R: +1 R = Gewinn in Höhe des Risikos; alle Kosten (Spread, Kommission) abgezogen

## Je Strategie über alle Märkte

| strategy | is_trades | is_avg_r | is_t | is_win_pct | oos_trades | oos_avg_r | oos_t | oos_win_pct |
|---|---|---|---|---|---|---|---|---|
| ASIA_MR | 2005 | -0.118 | -3.67 | 30.3 | 833 | -0.091 | -1.73 | 28.8 |
| MOMO | 8062 | -0.127 | -8.56 | 32.3 | 3720 | -0.094 | -4.22 | 32.4 |
| TWAP_MR | 14261 | -0.08 | -5.65 | 26.3 | 6830 | -0.097 | -4.73 | 25.3 |
| ORB | 5549 | -0.079 | -5.2 | 40.0 | 2051 | -0.109 | -4.24 | 37.8 |
| FIX_FADE | 18 | -0.206 | -1.17 | 27.8 | 23 | -0.127 | -0.73 | 47.8 |
| SQUEEZE | 1028 | -0.175 | -4.18 | 27.9 | 325 | -0.216 | -2.94 | 26.8 |

## Treffer im Lernzeitraum (t >= 2.0): 0 von 95
Bei reinem Zufall wären etwa 2 zu erwarten.

## Bestehen auch den Prüfzeitraum

**Keine Kombination besteht beide Zeiträume.**

## Beste 15 im Lernzeitraum (zur Einordnung)

| symbol | strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | oos_pf | oos_max_dd_r | minlot_risk | minlot_risk_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NZDJPY | TWAP_MR | 69 | 0.493 | 1.86 | 23 | 0.073 | 0.16 | 1.09 | 5.4 | 0.46 | 2.4 |
| EURUSD | ASIA_MR | 32 | 0.413 | 1.47 | 1 | -1.112 | 0.0 | 0.0 | 1.1 | 0.41 | 2.2 |
| USDJPY | SQUEEZE | 30 | 0.371 | 1.35 | 12 | -0.094 | -0.22 | 0.87 | 3.3 | 0.35 | 1.8 |
| EURCHF | ORB | 47 | 0.167 | 0.97 | 4 | -0.754 | -2.54 | 0.04 | 3.1 | 0.78 | 4.1 |
| EURAUD | TWAP_MR | 52 | 0.159 | 0.6 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.74 | 3.9 |
| US100 | SQUEEZE | 161 | 0.06 | 0.53 | 76 | -0.237 | -1.57 | 0.68 | 25.0 | nan | nan |
| GBPJPY | TWAP_MR | 182 | 0.071 | 0.51 | 74 | -0.231 | -1.05 | 0.73 | 25.0 | 0.73 | 3.8 |
| XAGUSD | MOMO | 482 | 0.013 | 0.21 | 225 | -0.181 | -2.08 | 0.74 | 50.3 | 12.36 | 65.1 |
| AUDUSD | TWAP_MR | 83 | 0.023 | 0.11 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.59 | 3.1 |
| XAUUSD | ASIA_MR | 262 | 0.004 | 0.04 | 103 | -0.092 | -0.62 | 0.87 | 18.5 | 5.38 | 28.3 |
| US500 | ORB | 169 | 0.003 | 0.03 | 86 | -0.161 | -1.3 | 0.75 | 18.5 | nan | nan |
| GBPCHF | ORB | 49 | 0.002 | 0.02 | 2 | -0.73 | -2.43 | 0.0 | 1.5 | 1.35 | 7.1 |
| USDCAD | TWAP_MR | 153 | -0.015 | -0.1 | 12 | -0.24 | -0.39 | 0.74 | 6.7 | 0.34 | 1.8 |
| UK100 | MOMO | 569 | -0.007 | -0.12 | 346 | -0.092 | -1.28 | 0.86 | 55.6 | nan | nan |
| GER40 | MOMO | 533 | -0.008 | -0.13 | 329 | -0.012 | -0.16 | 0.98 | 36.7 | nan | nan |