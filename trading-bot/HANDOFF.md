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
4. `python -m research.run --source mt5 --days 365` → testet **alle handelbaren Symbole** auf M1
   mit echten Fusion-Spreads → `research_out/report.md`
5. Bericht mit dem Nutzer ehrlich auswerten. Eine Strategie zählt nur, wenn sie IS t ≥ 2, ≥ 30 Trades
   **und** OOS positiv erreicht. Vorsicht vor Zufallstreffern bei vielen Kombinationen.
   Keine Parameter auf den Prüfzeitraum optimieren.

## Offline-Ergebnisse aus der Cloud (HistData + gemessene Dukascopy-Spreads)
Siehe `research/RESULTS_histdata.md`, falls vorhanden. Erster Teiltest auf EURUSD und GBPUSD:
keine Kombination besteht beide Zeiträume. Auf M1 frisst der Kostenfilter die meisten Signale
mit ATR-Stops, weil Spread und Kommission im Verhältnis zum Stop zu teuer sind.

## Wie der Nutzer kommuniziert werden will
Deutsch. Als ehrlicher Berater, nicht als Ja-Sager: unbequeme Wahrheit zuerst,
Aussagen mit [Certain]/[Likely]/[Guessing] kennzeichnen, bei Widerspruch nicht
einknicken ohne neue Information.
