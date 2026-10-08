# Ergebnis: 9 Kombinationen der 6 Strategien auf M1, M15 und H1

**Kurz: Kombinieren hilft nicht.** 27 Kombinationen (9 Regeln x 3 Zeitrahmen), über ~30 Märkte:
Im Validierungszeitraum (Jan 2024 - Sep 2025) sind 26 von 27 negativ. Die eine Ausnahme
(ASIA_MR+RANGE auf M1, +0,043 R) beruht auf nur 72 Trades und war im Lernzeitraum klar negativ.
Von 405 einzelnen Markt-Kombinationen waren im Lernzeitraum nur 2 auffällig. Per Zufall wären ~9 zu
erwarten gewesen. Formal besteht eine alle Hürden, sie lässt sich aber vollständig durch den
Nasdaq-Aufwärtstrend erklären (siehe unten).

## Die 9 Kombinationen (vorab festgelegt, `research/combos.py`)
| Kombination | Idee |
|---|---|
| ALL6 | Portfolio: alle 6 Strategien gleichzeitig |
| ORB+TREND | Eröffnungs-Ausbruch nur in Trendrichtung |
| SQUEEZE+TREND | Volatilitäts-Ausbruch nur in Trendrichtung |
| ORB+COMPRESSED | Eröffnungs-Ausbruch nur nach ruhiger Vorphase |
| TWAP_MR+RANGE | Rückkehr zum Tagesdurchschnitt nur ohne Trend (ADX < 20) |
| ASIA_MR+RANGE | Asien-Überdehnung nur ohne Trend |
| FIX_FADE+STRETCH | Fix-Konter nur bei Kurs weit weg vom Tagesdurchschnitt |
| VOTE2 | Einstieg, wenn >= 2 Strategien kurz hintereinander dieselbe Richtung zeigen |
| REGIME | Trend-Strategien bei Trend (ADX >= 25), Rückkehr-Strategien bei Seitwärts (ADX < 20) |

## H1
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| FIX_FADE+STRETCH | 612 | -0.007 | -0.21 | 317 | 0.04 | 0.81 | 1748 | -0.06 | -3.01 |
| ORB+TREND | 3209 | -0.039 | -2.29 | 1651 | -0.021 | -0.87 | 8581 | -0.067 | -6.43 |
| ALL6 | 9973 | -0.044 | -4.49 | 5229 | -0.031 | -2.25 | 27503 | -0.071 | -12.15 |
| SQUEEZE+TREND | 216 | 0.026 | 0.34 | 110 | -0.033 | -0.29 | 657 | -0.116 | -2.65 |
| TWAP_MR+RANGE | 118 | 0.15 | 1.7 | 52 | -0.048 | -0.37 | 376 | -0.086 | -1.77 |
| ORB+COMPRESSED | 2465 | -0.054 | -2.73 | 1390 | -0.062 | -2.3 | 7241 | -0.065 | -5.67 |
| REGIME | 4076 | -0.056 | -3.7 | 2175 | -0.063 | -2.93 | 11011 | -0.067 | -7.3 |
| VOTE2 | 877 | -0.049 | -1.61 | 469 | -0.082 | -1.89 | 2488 | -0.06 | -3.19 |
| ASIA_MR+RANGE | 12 | 0.169 | 0.75 | 5 | -0.4 | -1.2 | 18 | -0.379 | -2.93 |

## M15
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| ASIA_MR+RANGE | 29 | -0.185 | -0.98 | 17 | 0.055 | 0.21 | 64 | -0.078 | -0.59 |
| ORB+TREND | 3218 | -0.08 | -4.16 | 1427 | -0.033 | -1.07 | 8399 | -0.097 | -8.16 |
| ORB+COMPRESSED | 2696 | -0.071 | -3.31 | 1221 | -0.079 | -2.38 | 7041 | -0.112 | -8.44 |
| REGIME | 5554 | -0.093 | -5.94 | 2530 | -0.083 | -3.48 | 14701 | -0.113 | -11.71 |
| ALL6 | 16259 | -0.072 | -7.55 | 7383 | -0.108 | -7.62 | 43300 | -0.114 | -19.93 |
| VOTE2 | 1439 | -0.071 | -2.08 | 629 | -0.152 | -2.96 | 3550 | -0.116 | -5.33 |
| SQUEEZE+TREND | 255 | -0.033 | -0.38 | 105 | -0.175 | -1.33 | 660 | -0.198 | -3.81 |
| FIX_FADE+STRETCH | 274 | -0.129 | -2.42 | 166 | -0.209 | -2.96 | 842 | -0.112 | -3.56 |
| TWAP_MR+RANGE | 487 | 0.005 | 0.08 | 206 | -0.26 | -3.27 | 1559 | -0.142 | -4.74 |

## M1
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| ASIA_MR+RANGE | 41 | -0.26 | -1.26 | 20 | 0.15 | 0.47 | 72 | 0.043 | 0.27 |
| TWAP_MR+RANGE | 5855 | -0.101 | -4.86 | 2687 | -0.088 | -2.86 | 13448 | -0.104 | -7.49 |
| REGIME | 13935 | -0.112 | -9.31 | 6248 | -0.09 | -4.97 | 33782 | -0.137 | -17.78 |
| VOTE2 | 1285 | -0.169 | -4.49 | 515 | -0.092 | -1.51 | 2596 | -0.16 | -5.98 |
| ALL6 | 30923 | -0.098 | -11.56 | 13782 | -0.1 | -7.77 | 73885 | -0.129 | -23.62 |
| ORB+TREND | 3008 | -0.066 | -3.22 | 1127 | -0.114 | -3.3 | 7255 | -0.128 | -9.68 |
| FIX_FADE+STRETCH | 17 | -0.157 | -0.88 | 23 | -0.127 | -0.73 | 78 | -0.27 | -2.81 |
| ORB+COMPRESSED | 853 | -0.089 | -2.23 | 412 | -0.179 | -3.08 | 2033 | -0.124 | -4.77 |
| SQUEEZE+TREND | 492 | -0.223 | -3.76 | 157 | -0.222 | -2.13 | 821 | -0.127 | -2.64 |

## Der einzige formale Überlebende: US100 + ORB+TREND (H1)
IS +0,146 R (t 2,1), OOS +0,017 R (t 0,2), VAL +0,049 R (t 1,1). Bei genauerem Hinsehen ist das
kein Timing-Vorteil:
- 246 von 305 Trades enden nicht an Stop oder Ziel, sondern am Zwangsausstieg am Abend.
  Faktisch heißt die Regel: "Nasdaq nachmittags kaufen, wenn er steigt, bis abends halten."
- 2/3 sind Käufe, nur sie verdienen. Das ist der Nasdaq-Aufwärtstrend 2024-2026.
- Dieselbe Regel bringt auf US500 -0,015 R und auf GER40, UK100 und JPN225 ebenfalls nichts.
- Sie war die beste von 142 H1-Kombinationen und erreicht über alle Zeiträume nur t = 1,9.

## Folgerung
Kombiniert man Bausteine, die vor Kosten keinen Vorteil haben, bleibt der Vorteil bei null.
Filter reduzieren die Anzahl der Trades, nicht den Kostennachteil pro Trade. Portfolios
verteilen das Risiko, ändern aber nicht das Vorzeichen.

## Reproduzieren
```bash
python -m research.run --source histdata --set combos --tf 60 --split 2026-06-01 --val-folder data/histdata_old
```
