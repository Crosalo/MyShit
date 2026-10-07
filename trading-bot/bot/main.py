"""Hauptschleife des Bots.

Start:  python -m bot.main --config config.yaml
Not-Aus: Datei state/STOP anlegen (schließt alle Bot-Positionen, keine neuen Trades)
         oder Telegram /stop bzw. /flat.
"""
import argparse
import csv
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .broker import Broker, BrokerError, LiveTradingBlocked, load_mt5_module
from .config import load_config
from .news import Event, NewsCalendar
from .notifier import Notifier
from .risk import DailyGuard, position_size
from .scanner import scan
from .session import in_trade_window, must_be_flat
from .strategy import Signal, TrendPullback

log = logging.getLogger("bot")


def setup_logging(log_dir: str):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(log_dir) / "bot.log", encoding="utf-8"),
        ],
    )


def describe_block(block) -> str:
    if isinstance(block, Event):
        return f"{block.currency} {block.title} um {block.time_utc:%H:%M} UTC"
    return str(block)


class TradingBot:
    def __init__(self, cfg: dict, broker: Broker, notifier: Notifier, news: NewsCalendar,
                 clock=lambda: datetime.now(timezone.utc)):
        self.cfg = cfg
        self.broker = broker
        self.notifier = notifier
        self.news = news
        self.clock = clock
        state_dir = Path(cfg["state_dir"])
        self.guard = DailyGuard(
            cfg["risk"]["max_daily_loss_pct"],
            cfg["risk"]["max_trades_per_day"],
            state_dir / "daily.json",
        )
        self.strategy = TrendPullback(cfg["strategy"])
        self.kill_file = state_dir / "STOP"
        self.kill_active = False
        self.journal = Path(cfg["log_dir"]) / "trades.csv"
        self.last_bar: dict = {}
        self.specs: dict = {}

    # ---------- Start ----------
    def startup(self):
        acc = self.broker.connect()
        for sym in self.cfg["symbols"]:
            spec = self.broker.spec(sym)
            if spec is None:
                log.warning("Symbol %s gibt es bei diesem Broker nicht - übersprungen", sym)
                continue
            self.specs[sym] = spec
        if not self.specs:
            raise BrokerError("Keines der konfigurierten Symbole ist verfügbar")
        mode = "DEMO" if self.broker.is_demo() else "ECHTGELD"
        self.notifier.send(
            f"Bot gestartet | {acc.company} | Konto {acc.login} ({mode}) | "
            f"Equity {acc.equity:.2f} {acc.currency} | Märkte: {', '.join(self.specs)}"
        )

    # ---------- Steuerung ----------
    def status_text(self, equity: float) -> str:
        lines = [f"Equity {equity:.2f} | Trades heute {self.guard.trades}"]
        ok, reason = self.guard.can_open()
        lines.append("Handel aktiv" if ok else f"Kein neuer Handel: {reason}")
        for p in self.broker.positions():
            lines.append(f"{p.symbol} {'BUY' if p.type == 0 else 'SELL'} {p.volume} | P/L {p.profit:.2f}")
        for ev in self.news.upcoming(self.clock(), 12):
            lines.append(f"News: {ev.time_utc:%a %H:%M} UTC {ev.currency} {ev.title}")
        return "\n".join(lines)

    def handle_commands(self, equity: float):
        for cmd in self.notifier.poll_commands():
            if cmd == "/stop":
                self.guard.manual_stop = True
                self.guard.save()
                self.notifier.send("Gestoppt: keine neuen Trades. /flat schließt Positionen, /resume startet wieder.")
            elif cmd == "/resume":
                self.guard.manual_stop = False
                self.guard.save()
                self.notifier.send("Fortgesetzt.")
            elif cmd == "/flat":
                n = self.broker.close_all()
                self.notifier.send(f"{n} Position(en) geschlossen.")
            elif cmd == "/status":
                self.notifier.send(self.status_text(equity))

    # ---------- Ein Durchlauf ----------
    def step(self):
        now = self.clock()
        equity = self.broker.equity()
        if self.guard.roll_day(now.date().isoformat(), equity):
            log.info("Neuer Handelstag, Start-Equity %.2f", equity)
        self.handle_commands(equity)

        if self.kill_file.exists():
            if not self.kill_active:
                n = self.broker.close_all()
                self.kill_active = True
                self.notifier.send(f"NOT-AUS (STOP-Datei): {n} Position(en) geschlossen, kein Handel.")
            return
        if self.kill_active:
            self.kill_active = False
            self.notifier.send("STOP-Datei entfernt, Handel wieder freigegeben.")

        if self.guard.loss_breached(equity) and not self.guard.halted:
            n = self.broker.close_all()
            self.guard.halt(f"Tagesverlust-Limit {self.cfg['risk']['max_daily_loss_pct']}% erreicht")
            self.notifier.send(f"Tagesverlust-Limit erreicht: {n} Position(en) geschlossen, Pause bis morgen.")

        session = self.cfg["session"]
        if must_be_flat(now, session) and self.broker.positions():
            n = self.broker.close_all()
            self.notifier.send(f"Handelsende: {n} Position(en) geschlossen.")

        if not in_trade_window(now, session) or not self.guard.can_open()[0]:
            return

        self.news.refresh()
        candidates = self.scan_markets()
        for res, sig in candidates:
            ok, reason = self.guard.can_open()
            if not ok:
                log.info("Keine weiteren Trades: %s", reason)
                break
            if len(self.broker.positions()) >= self.cfg["risk"]["max_open_positions"]:
                log.info("Max. offene Positionen erreicht")
                break
            if self.broker.positions(res.symbol):
                continue
            block = self.news.blocking_event(res.symbol, now)
            if block:
                log.info("%s: Signal verworfen, News-Sperre (%s)", res.symbol, describe_block(block))
                continue
            self.open_trade(res.symbol, sig, equity)

    def scan_markets(self) -> list:
        tf = self.cfg["strategy"]["timeframe"]
        offset = self.broker.server_offset_hours(list(self.specs))
        candidates = []
        for sym in self.specs:
            df = self.broker.rates(sym, tf, self.strategy.min_bars + 100, offset)
            if df is None or len(df) < self.strategy.min_bars + 2:
                continue
            i = len(df) - 2  # letzte GESCHLOSSENE Kerze
            bar_time = df["time"].iloc[i]
            if self.last_bar.get(sym) == bar_time:
                continue
            self.last_bar[sym] = bar_time
            tick = self.broker.tick(sym)
            if tick is None:
                continue
            d = self.strategy.prepare(df)
            res = scan(sym, d, i, tick.ask - tick.bid, self.cfg["scanner"])
            sig = self.strategy.signal_at(d, i) if res.tradable else None
            log.info(
                "%s %s | ADX %.1f | Spread/ATR %.0f%% | %s | %s",
                sym, f"{bar_time:%H:%M}", res.adx, res.spread_atr_ratio * 100,
                res.reason, sig.reason if sig else "kein Signal",
            )
            if sig:
                candidates.append((res, sig))
        candidates.sort(key=lambda c: c[0].score, reverse=True)
        return candidates

    def open_trade(self, symbol: str, sig: Signal, equity: float):
        spec = self.specs[symbol]
        risk = self.cfg["risk"]
        size = position_size(equity, risk["risk_per_trade_pct"], sig.sl_distance, spec, risk["commission_per_lot"])
        if size.lots <= 0:
            log.info("%s: Signal übersprungen - %s", symbol, size.reason)
            return
        try:
            request = self.broker.build_market_request(
                symbol, sig.side, size.lots, sig.sl_distance, sig.tp_distance, spec, "trend-pullback"
            )
            result = self.broker.send(request)
        except BrokerError as exc:
            log.error("%s", exc)
            self.notifier.send(f"Order-Fehler {symbol}: {exc}")
            return
        self.guard.record_trade()
        self.write_journal(symbol, sig, size, request, result)
        self.notifier.send(
            f"{sig.side.upper()} {symbol} {size.lots} Lot @ {result.price} | SL {request['sl']} | "
            f"TP {request['tp']} | Risiko {size.risk_money:.2f} ({size.risk_pct:.1f}%) | {sig.reason}"
        )

    def write_journal(self, symbol, sig, size, request, result):
        new = not self.journal.exists()
        with self.journal.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time_utc", "symbol", "side", "lots", "price", "sl", "tp",
                            "order", "risk_money", "risk_pct", "reason"])
            w.writerow([self.clock().isoformat(), symbol, sig.side, size.lots, result.price,
                        request["sl"], request["tp"], result.order, round(size.risk_money, 2),
                        round(size.risk_pct, 2), sig.reason])

    # ---------- Endlosschleife ----------
    def run(self):
        self.startup()
        errors = 0
        while True:
            try:
                self.step()
                errors = 0
            except LiveTradingBlocked:
                raise
            except Exception as exc:
                errors += 1
                log.exception("Fehler in der Hauptschleife")
                if errors == 1 or errors % 30 == 0:
                    self.notifier.send(f"Fehler ({errors}x): {exc}")
                if errors >= 3:
                    try:
                        self.broker.shutdown()
                        self.broker.connect()
                    except Exception:
                        log.exception("Neuverbindung fehlgeschlagen")
            time.sleep(self.cfg["loop"]["poll_seconds"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="MT5 Daytrading-Bot")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    setup_logging(cfg["log_dir"])
    broker = Broker(load_mt5_module(cfg["mt5"]), cfg["mt5"])
    notifier = Notifier(cfg["telegram"]["enabled"])
    news = NewsCalendar(cfg["news"], Path(cfg["state_dir"]) / "calendar.json")
    bot = TradingBot(cfg, broker, notifier, news)
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Beendet. Offene Positionen bleiben mit SL/TP beim Broker bestehen.")
    except LiveTradingBlocked as exc:
        log.error("%s", exc)
        sys.exit(2)
    finally:
        try:
            broker.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
