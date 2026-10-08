# Ergebnisse der Mac-Session (07.–08.10.2026) – echte Fusion-Daten aus MT5

Daten: das Echtgeld-Konto bei FusionMarkets-Live, über die MQL5-Skripte in `mql5/Scripts/` exportiert,
weil das Python-Paket `MetaTrader5` auf dem Mac (Wine) nicht läuft. Leser: `research/mt5_files.py`
(`--source mt5files` in `research.run`). Spread je Stunde aus echten Ticks (`SpreadProfile.mq5`),
weil der Bar-Spread beim Raw-Konto in 96 % der FX-Minuten 0 ist. Alle Ergebnisse nach Kosten.

Verfügbare Historie bei `Max. Balken = 100000`: M1 ~3 Monate, M5 ~1 Jahr, H1 dicht ab Mitte 2019,
D1 ab 1997. Aktien-CFDs (104 Stück, 0 Kommission, Mindestlot 0,1): M5 ~5 Jahre.

## Kurzfassung: nichts besteht

| Test | Modul | Ergebnis |
|---|---|---|
| 6 Cloud-Strategien, M1 (31 Märkte) | `research.run` | 1 von 109 im IS t ≥ 2, OOS ~0 |
| 6 Cloud-Strategien, M5 | `research.run` | 0 von 133 |
| Saisonalität (TwinTraders), Walk-Forward 2008–2026 | `research.seasonal` | 52,2 % Treffer statt versprochener 92 % |
| ICT Sweep/BOS/FVG, H1 2019–2026 | `research.ict` | IS −0,142R, OOS −0,079R; mit Filtern nicht besser |
| Break & Retest 9:30 (Dennis Trades, Scarface) | `research.break_retest` | ~30 % Treffer bei 2R, −0,11R |
| 9 weitere YouTube-Strategien | `research.videos` | alle über alle Märkte negativ |
| 12 Einstiege × bis zu 3 von 7 Filtern | `research.video_combos` | M5/M15 0 von 698 ausgewählt, H1 3 von 307, 0 bestanden |
| 17 Strategien × M1/M2/M3/M5/M10/M15/M30 | `research.tf_sweep` | 0 von 200 Zellen; je kleiner der Zeitrahmen, desto schlechter |
| Market Intraday Momentum (Gao 2018, Baltussen 2021) | `research.momentum` | 1 Jahr M5: negativ (sogar brutto). Letzte Stunde H1 2019–2026: +1,4 bp/Tag, t=1,45, Gewinne nur 2020/22/23 |
| Noise-Boundary-Momentum (Zarattini 2024) | `research.momentum` | US100 +2,5 %, US500 −7,7 %, US30 −3,5 % (1 Jahr) |
| ORB "Stocks in Play" (Zarattini 2024), 70 Aktien-CFDs, 2021–2026 | `research.orb_stocks` | M5 kann die Einstiegskerze nicht auflösen: bester Fall Top 5 +0,09R, schlechtester −0,63R. Offen, braucht M1/Ticks |

## Offene Spuren
- ~~TwinTraders H1-FVG + Sweep/BOS auf US-Indizes M1~~: Out-of-Sample 11/2020–06/2026 mit
  `research.twin_oos` geprüft. Die frühere Plusrechnung kam von Zukunftswissen im Kursziel (laufende,
  unfertige H1-Kerze). Nach Korrektur −0,010R, t=−0,24, 1.407 Trades: **nicht bestanden**.
- ORB auf Aktien-CFDs: nur mit M1 oder Ticks entscheidbar.

## Fallen, die schon einmal Scheinergebnisse erzeugt haben
- **Werte aus höheren Zeitrahmen nur von FERTIGEN Kerzen nehmen** (Kerzenende <= Signalzeit).
  Die laufende H1-Kerze im Kursziel machte TwinTraders scheinbar profitabel (t=3,8 statt −0,2).
- **Serverzeit nie mit festem Versatz umrechnen.** Fusion ist ein NY-Close-Server (UTC+2/+3).
  Mit festen −3 h lagen H1/D1-Filter im Winter eine Stunde in der Zukunft; "Sneaky Pivot + H1-Trend"
  sah dadurch wie ein Gewinner aus und verschwand nach der Korrektur. Immer `server_epoch_to_utc`.
- **Große Exporte füllen die Platte.** MT5 lädt dafür Historie nach (~140 MB je Aktie). Am 08.10.
  lief die Mac-Platte voll, MT5 hing 4,5 Stunden, die Live-EAs standen. Vorher Platz prüfen,
  in kleinen Paketen exportieren.
