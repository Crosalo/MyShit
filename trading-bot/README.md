# MT5 Daytrading-Bot (Fusion Markets)

> **Stand: Testprojekt, nur für Demokonten.** Der Bot startet nicht auf einem Echtgeld-Konto,
> solange du das nicht ausdrücklich an zwei Stellen freigibst (siehe unten).

## Ehrliche Ausgangslage

Backtest der eingebauten Basis-Strategie auf echten Kursen (Yahoo-Daten, inkl. Spread und
4,50 Kommission/Lot, 1 % Risiko pro Trade):

| Markt / Zeitraum | Start 19 € | Start 1000 € |
|---|---|---|
| EURUSD M15, 12 Wochen | 0 Trades (139 abgelehnt: Mindestlot = 6 % Risiko) | 79 Trades, PF 0,97, −1,5 % |
| GBPUSD M15, 12 Wochen | 0 Trades | 83 Trades, PF 0,77, −10,7 % |
| EURUSD H1, 2,8 Jahre | 0 Trades (Mindestlot = 13 % Risiko) | 329 Trades, PF 1,01, +1,6 % |
| GBPUSD H1, 2,8 Jahre | 0 Trades | 341 Trades, PF 0,94, −8,3 % |
| Gold H1, 2,4 Jahre | 0 Trades (Mindestlot = 137 % Risiko) | 44 Trades, PF 1,09 (zu wenige für eine Aussage) |

Was das bedeutet:
- **Die Basis-Strategie hat keinen nachweisbaren Vorteil.** Profit-Faktor ~1 heißt: nach Kosten Nullsummenspiel.
  Sie ist das Testobjekt, an dem die Technik geprüft wird, kein Geldautomat.
- **Mit 19 € kann der Bot nicht verantwortungsvoll handeln.** Schon 0,01 Lot (das Minimum) riskiert
  6–137 % des Kontos pro Trade. Wer das Risiko-Limit auf 15 % hochdreht, landet im Backtest nach
  15–17 Trades bei 5–7 € – dann ist selbst das Mindestlot zu groß und der Bot steht still.

## Was der Bot macht

Alle 20 Sekunden, für jede neu geschlossene M15-Kerze:

1. **Marktauswahl (Scanner):** prüft alle Kandidaten (EURUSD, GBPUSD, USDJPY, AUDUSD, XAUUSD …).
   Handelbar ist nur, wo der Spread im Verhältnis zur normalen Bewegung (ATR) billig ist.
   Sortiert nach Trendstärke (ADX).
2. **Chartanalyse (Strategie):** Trend-Pullback – EMA 20/50/200 in Trendrichtung, ADX ≥ 20, Kurs läuft an die
   EMA20 zurück und dreht wieder. Stop 1,5 × ATR, Ziel 2 × Stop.
3. **News-Filter:** ForexFactory-Wirtschaftskalender. 30 Min. vor/nach High-Impact-Terminen
   (NFP, CPI, Zinsentscheide …) keine neuen Trades in den betroffenen Währungen.
   Ist der Kalender nicht ladbar, wird nicht gehandelt.
4. **Risiko:** Positionsgröße so, dass Stop + Kommission ≤ 1 % der Equity. Unter Mindestlot → kein Trade.
5. **Order** mit festem Stop-Loss und Take-Profit beim Broker (bleiben bestehen, auch wenn der Bot abstürzt).

### Sicherungen

| Sicherung | Wirkung |
|---|---|
| Demo-Sperre | Echtgeld nur mit `allow_live: true` **und** Umgebungsvariable `BOT_LIVE_CONFIRM=ICH-AKZEPTIERE-TOTALVERLUST` |
| Tagesverlust 3 % | alle Bot-Positionen schließen, Pause bis zum nächsten Tag (überlebt Neustarts) |
| Max. 2 Positionen, 6 Trades/Tag | gegen Order-Schleifen |
| 1 Signal pro Kerze und Symbol | kein doppeltes Einsteigen nach Fehlern/Neustarts |
| Handelsende 20:45 UTC, Freitag 19:30 UTC | keine Positionen über Nacht/Wochenende |
| Not-Aus | Datei `state/STOP` anlegen oder Telegram `/stop` + `/flat` |
| Magic Number | Bot fasst nur eigene Trades an, nie deine manuellen |

## Einrichtung auf deinem Windows-PC

1. **Python 3.12** von python.org installieren (Haken bei „Add Python to PATH“).
2. Bei Fusion Markets im Client-Hub ein **MT5-Demokonto** eröffnen und im MT5-Terminal damit einloggen.
3. Im MT5-Terminal: *Extras → Optionen → Expert Advisors → „Algorithmischen Handel erlauben“*
   und in der Symbolleiste den Knopf **Algo Trading** auf grün stellen.
4. Im Ordner `trading-bot` (Eingabeaufforderung):
   ```bat
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy config.example.yaml config.yaml
   ```
5. **Check** (handelt nicht):
   ```bat
   python -m bot.check --list   :: alle Symbolnamen des Brokers
   python -m bot.check          :: Konto, Demo/Echt, Spreads, Mindestlot-Risiko
   ```
6. **Backtest mit deinen Broker-Daten:**
   ```bat
   python -m bot.export_history --days 365
   python -m bot.backtest --csv data\EURUSD_M15.csv --spec data\EURUSD_spec.json --equity 1000
   ```
7. **Starten** (MT5 muss laufen):
   ```bat
   python -m bot.main
   ```
   Log: `logs\bot.log`, Trades: `logs\trades.csv`. Beenden mit Strg+C (Positionen behalten SL/TP).

### Telegram (optional)

1. In Telegram `@BotFather` → `/newbot` → Token kopieren.
2. Dem neuen Bot eine Nachricht schreiben, dann `https://api.telegram.org/bot<TOKEN>/getUpdates`
   öffnen und `chat.id` ablesen.
3. `setx TELEGRAM_TOKEN "<TOKEN>"` und `setx TELEGRAM_CHAT_ID "<ID>"`, neues Fenster öffnen,
   in `config.yaml` `telegram: enabled: true`.
4. Befehle: `/status`, `/stop` (keine neuen Trades), `/flat` (alles schließen), `/resume`.

## Strategie-Forschung auf M1 (`research/`)

Sechs eigenständige Strategien aus verschiedenen Familien (Details in `research/strategies.py`):
ORB (Eröffnungs-Ausbruch), ASIA_MR (ruhige Asien-Session), SQUEEZE (Volatilitäts-Ausbruch),
TWAP_MR (Rückkehr zum Session-Durchschnitt), MOMO (Trend-Ausbruch), FIX_FADE (London-Fix kontern).
Parameter sind vorab festgelegt, nicht auf die Daten optimiert.

**Auf deinem PC mit MT5** (alle handelbaren Symbole, echte Fusion-Spreads):
```bat
python -m research.run --source mt5 --days 365
```
Für lange M1-Historie in MT5 vorher *Extras → Optionen → Charts → Max. Balken im Chart* auf „Unbegrenzt“ stellen.
Ergebnis: `research_out\report.md` (Übersicht), `summary.csv`, `trades.csv.gz`.

Bewertung: zählt nur, wenn im Lernzeitraum klar positiv (t ≥ 2, ≥ 30 Trades) **und** im
unberührten Prüfzeitraum (letztes Drittel) weiterhin positiv. Kosten sind abgezogen, Trades mit
Kosten > 20 % des Risikos werden gar nicht erst eröffnet.

## Hostinger-VPS (Stufe 2, noch nicht umgesetzt)

Dein VPS (KVM 2, Ubuntu 24.04 + Docker) kann den Bot 24/5 betreiben, aber MT5 ist ein
Windows-Programm. Plan: MT5 unter Wine im Docker-Container, der Bot spricht über `mt5linux`
(`bridge: rpyc` in der Config). Das lohnt sich erst, wenn die Demo-Phase etwas zeigt –
bis dahin läuft alles kostenlos auf dem PC.

## Bevor echtes Geld ins Spiel kommt

- [ ] Backtest mit Broker-Daten über ≥ 1 Jahr: Profit-Faktor deutlich > 1,2 nach Kosten
- [ ] ≥ 6 Wochen Demo-Betrieb ohne technische Fehler, Ergebnis ähnlich wie im Backtest
- [ ] Kontogröße, bei der das Mindestlot ≤ 1 % Risiko bedeutet (EURUSD M15: ~120 €, Gold: deutlich mehr)
- [ ] Nur Geld, dessen Totalverlust dich nicht trifft

## Tests

```bash
python -m pytest
```
