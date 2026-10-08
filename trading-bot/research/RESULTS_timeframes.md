# Ergebnis: 6 Strategien x 30 Märkte auf M1, M15 und H1

**Kurz: Keine Strategie funktioniert, auf keinem Zeitrahmen.** 18 Kombinationen aus Strategie und
Zeitrahmen, je über ~30 Märkte: Keine besteht Lernzeitraum + Prüfzeitraum + Validierung. Im
Validierungszeitraum (Jan 2024 - Sep 2025, vorher nie angesehen) sind alle 18 negativ, die meisten
deutlich (t bis -17).

## Aufbau
- **IS** (Lernzeitraum): Okt 2025 - Mai 2026
- **OOS** (Prüfzeitraum): Jun - Sep 2026
- **VAL** (Validierung): Jan 2024 - Sep 2025, erst nach Festlegung aller Parameter geladen
- Parameter je Zeitrahmen vor dem Test festgelegt (`research/strategies.py`, `TF_PARAMS`)
- Signale auf M1/M15/H1, Ausstiege immer auf der echten M1-Kursfolge simuliert
- Kosten: gemessene Dukascopy-Spreads je UTC-Stunde + 4,50 USD/Lot Kommission (FX, Metalle)

## H1
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| TWAP_MR | 571 | -0.023 | -0.56 | 294 | 0.117 | 2.09 | 1632 | -0.108 | -4.54 |
| FIX_FADE | 686 | -0.017 | -0.52 | 358 | 0.03 | 0.64 | 2024 | -0.072 | -3.82 |
| MOMO | 1879 | -0.039 | -1.7 | 1001 | -0.018 | -0.54 | 5224 | -0.099 | -7.23 |
| ORB | 6299 | -0.051 | -4.17 | 3296 | -0.047 | -2.72 | 17149 | -0.058 | -7.86 |
| SQUEEZE | 413 | -0.036 | -0.65 | 225 | -0.098 | -1.27 | 1265 | -0.083 | -2.61 |
| ASIA_MR | 125 | -0.009 | -0.16 | 55 | -0.223 | -2.78 | 209 | -0.066 | -1.44 |

## M15
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| ORB | 6732 | -0.075 | -5.71 | 2926 | -0.087 | -4.19 | 17392 | -0.09 | -10.92 |
| MOMO | 3731 | -0.086 | -4.04 | 1750 | -0.101 | -3.23 | 9963 | -0.143 | -11.3 |
| TWAP_MR | 4288 | -0.047 | -2.31 | 2004 | -0.116 | -4.02 | 12277 | -0.128 | -10.95 |
| ASIA_MR | 594 | -0.129 | -2.99 | 291 | -0.148 | -2.27 | 1321 | -0.103 | -3.57 |
| FIX_FADE | 376 | -0.116 | -2.56 | 195 | -0.178 | -2.72 | 1041 | -0.12 | -4.22 |
| SQUEEZE | 538 | -0.029 | -0.48 | 217 | -0.249 | -2.83 | 1306 | -0.102 | -2.68 |

## M1
| strategy | is_trades | is_avg_r | is_t | oos_trades | oos_avg_r | oos_t | val_trades | val_avg_r | val_t |
|---|---|---|---|---|---|---|---|---|---|
| ASIA_MR | 2005 | -0.118 | -3.67 | 833 | -0.091 | -1.73 | 3745 | -0.117 | -4.99 |
| MOMO | 8062 | -0.127 | -8.56 | 3720 | -0.094 | -4.22 | 20947 | -0.16 | -17.53 |
| TWAP_MR | 14261 | -0.08 | -5.65 | 6830 | -0.097 | -4.73 | 34082 | -0.122 | -13.42 |
| ORB | 5549 | -0.079 | -5.2 | 2051 | -0.109 | -4.24 | 13384 | -0.099 | -10.05 |
| FIX_FADE | 18 | -0.206 | -1.17 | 23 | -0.127 | -0.73 | 80 | -0.257 | -2.74 |
| SQUEEZE | 1028 | -0.175 | -4.18 | 325 | -0.216 | -2.94 | 1647 | -0.11 | -3.23 |

## Die zwei H1-Kandidaten waren Zufall
Im aktuellen Jahr sahen TWAP_MR (+0,108 R vor Kosten, OOS +0,117 R netto) und FIX_FADE (+0,091 R vor
Kosten) auf H1 vielversprechend aus. In den älteren Jahren verschwindet das:

| H1, Ø R pro Trade | vor Kosten (aktuelles Jahr) | vor Kosten (VAL) | netto (VAL) |
|---|---|---|---|
| TWAP_MR | +0,108 | -0,016 | -0,108 (1.632 Trades, t -4,5) |
| FIX_FADE | +0,091 | +0,020 | -0,072 (2.024 Trades, t -3,8) |
| ORB | +0,022 | +0,015 | -0,058 |
| MOMO | +0,037 | -0,032 | -0,099 |

**Folgerung:** Vor Kosten liegen alle 6 Ideen dauerhaft bei ungefähr 0 R. Sie enthalten keinen Vorteil.
Die Kosten machen daraus einen sicheren Verlust, auf M1 stärker als auf H1. Auch mit halbem Spread
bleibt im Validierungszeitraum alles negativ. Echte Fusion-Spreads ändern das Urteil daher sehr
wahrscheinlich nicht.

## Reproduzieren
```bash
python -m research.download_histdata --months 2025-10:2026-09 --out data/histdata
python -m research.download_histdata --years 2024 --months 2025-01:2025-09 --out data/histdata_old
python -m research.spreads --days 2026-09-15 2026-09-23
python -m research.run --source histdata --tf 60 --split 2026-06-01 --val-folder data/histdata_old
python -m research.costs --tf 60 --val
```
