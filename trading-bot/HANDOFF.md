# Übergabe: Stand des Projekts (für die nächste Claude-Sitzung)

## Ziel des Nutzers
Daytrading-Bot für **MT5 bei Fusion Markets**: Charts analysieren, News beachten, selbst
Märkte wählen und handeln. Später 24/5 auf dem **Hostinger-VPS** (KVM 2, Ubuntu 24.04 + Docker,
`srv1421899`, nächste Abbuchung 17,99 € am 24.10.2026). MT5 läuft auf dem Windows-PC des Nutzers.

## Harte Fakten, die nicht wegdiskutiert werden
- **Kapital: 19 €.** Schon das Mindestlot (0,01) riskiert bei normalem Stop 6–137 % des Kontos.
  Der Bot lehnt solche Trades bei 1 % Risiko ab. Erst echtes Geld, wenn eine Strategie
  auf Demo und im Prüfzeitraum besteht.
- **Nur Demokonto.** Der Bot verweigert Echtgeld-Konten, solange `allow_live: false` ist und
  die Variable `BOT_LIVE_CONFIRM` nicht gesetzt ist. Das bleibt so, bis die Checkliste in der README erfüllt ist.
- Die erste Strategie (Trend-Pullback, `bot/strategy.py`) hat **keinen Vorteil** (Profit-Faktor ~1).
  Der Nutzer will **eigene, neue Strategien**.

## Was fertig ist (Branch `claude/mt5-trading-bot`, Ordner `trading-bot/`)
- `bot/`: lauffähiger Bot (MT5-Anbindung, Demo-Sperre, Risiko-Limits, News-Filter über den
  ForexFactory-Kalender, Telegram, Not-Aus), Backtester, `bot.check`, `bot.export_history`.
- `research/`: **6 neue M1-Strategien** (ORB, ASIA_MR, SQUEEZE, TWAP_MR, MOMO, FIX_FADE) mit
  festen Parametern, eine M1-Engine in R inkl. Spread und Kommission, Trennung in Lern- und Prüfzeitraum.
- 55 Tests (`python -m pytest`).

## Nächster Schritt (auf dem PC des Nutzers, mit MT5)
1. Python 3.12, `cd trading-bot`, `pip install -r requirements.txt`, `copy config.example.yaml config.yaml`
2. MT5: Demokonto eingeloggt, Algo-Trading an, *Optionen → Charts → Max. Balken* = Unbegrenzt
3. `python -m bot.check` (Konto, Symbole, Spreads)
4. `python -m research.run --source mt5 --days 365 --tf 60` (auch `--tf 15`, `--tf 1`) → testet
   **alle handelbaren Symbole** mit echten Fusion-Spreads → `research_out/tf60/report.md`
5. Bericht mit dem Nutzer ehrlich auswerten. Eine Strategie zählt nur, wenn sie IS t ≥ 2, ≥ 30 Trades
   **und** OOS positiv erreicht. Vorsicht vor Zufallstreffern bei vielen Kombinationen.
   Keine Parameter auf den Prüfzeitraum optimieren.

## Offline-Ergebnisse aus der Cloud (HistData + gemessene Dukascopy-Spreads)
- `research/RESULTS_histdata.md`: M1, 30 Märkte. Nichts funktioniert, die Kosten (~0,1 R/Trade) fressen alles.
- `research/RESULTS_timeframes.md`: M1, M15 und H1 inkl. Validierung auf Jan 2024 - Sep 2025.
  **Alle 18 Kombinationen sind im Validierungszeitraum negativ.** Vor Kosten liegen alle Ideen bei
  ~0 R, haben also keinen Vorteil. Zwei H1-Kandidaten (TWAP_MR, FIX_FADE) waren Zufall.
- `research/RESULTS_combos.md`: 9 vorab festgelegte Kombinationen (Filter, Abstimmung, Regime,
  Portfolio) x 3 Zeitrahmen. 26 von 27 sind im Validierungszeitraum negativ. Einziger formaler
  Überlebender (US100 ORB+TREND H1) = Nasdaq-Aufwärtstrend, kein Vorteil.
- Der Nutzer meinte, er habe "viele Strategien geschickt". Angekommen ist nur ein TikTok-Link
  (QuiverQuant). Falls er Strategien nachreicht: als feste Regeln festhalten und genauso testen.
- Der MT5-Test auf dem PC ist die letzte Gegenprobe mit echten Fusion-Kosten. Erwartung: gleiches Urteil.

## Wie der Nutzer kommuniziert werden will
Deutsch. Als ehrlicher Berater, nicht als Ja-Sager: unbequeme Wahrheit zuerst,
Aussagen mit [Certain]/[Likely]/[Guessing] kennzeichnen, bei Widerspruch nicht
einknicken ohne neue Information.
