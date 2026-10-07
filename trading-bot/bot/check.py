"""Verbindungs- und Konto-Check, handelt NICHT.

python -m bot.check --config config.yaml

Zeigt: Demo/Echtgeld, Algo-Trading an/aus, welche Symbole es gibt, Spread,
und was ein Trade mit Mindestlot bei typischem Stop vom Konto riskieren würde.
"""
import argparse

from .broker import Broker, load_mt5_module
from .config import load_config
from .risk import position_size
from .strategy import TrendPullback


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--list", action="store_true", help="alle Symbolnamen des Brokers ausgeben")
    args = p.parse_args(argv)
    cfg = load_config(args.config)
    mt5 = load_mt5_module(cfg["mt5"])
    broker = Broker(mt5, {**cfg["mt5"], "allow_live": True})  # Check darf auch Echtkonten ansehen
    acc = broker.connect()
    if args.list:
        print(" ".join(sorted(s.name for s in mt5.symbols_get())))
        broker.shutdown()
        return
    term = mt5.terminal_info()
    print(f"Broker:       {acc.company} / {acc.server}")
    print(f"Konto:        {acc.login} ({'DEMO' if broker.is_demo() else 'ECHTGELD'})")
    print(f"Equity:       {acc.equity:.2f} {acc.currency}, Hebel 1:{acc.leverage}")
    print(f"Algo-Trading: {'AN' if term and term.trade_allowed else 'AUS -> im Terminal einschalten!'}")
    if not broker.is_demo() and not cfg["mt5"]["allow_live"]:
        print("Hinweis:      Bot würde auf diesem Konto NICHT starten (allow_live: false).")

    strategy = TrendPullback(cfg["strategy"])
    offset = broker.server_offset_hours(cfg["symbols"])
    print(f"Serverzeit:   UTC{offset:+g}\n")
    risk = cfg["risk"]
    print(f"{'Symbol':10} {'Spread':>8} {'Min-Lot':>8} {'Stop(1.5 ATR)':>14} {'Risiko Min-Lot':>16}")
    for sym in cfg["symbols"]:
        spec = broker.spec(sym)
        if spec is None:
            print(f"{sym:10} nicht verfügbar - Namen mit 'python -m bot.check --list' prüfen")
            continue
        df = broker.rates(sym, cfg["strategy"]["timeframe"], strategy.min_bars + 10, offset)
        tick = broker.tick(sym)
        if df is None or tick is None:
            print(f"{sym:10} keine Kursdaten")
            continue
        d = strategy.prepare(df)
        sl = cfg["strategy"]["sl_atr"] * d["atr"].iloc[-2]
        min_risk = spec.volume_min * (sl / spec.tick_size * spec.tick_value + risk["commission_per_lot"])
        size = position_size(acc.equity, risk["risk_per_trade_pct"], sl, spec, risk["commission_per_lot"])
        verdict = f"{size.lots} Lot ok" if size.lots else "ABGELEHNT"
        print(f"{sym:10} {tick.ask - tick.bid:8.{spec.digits}f} {spec.volume_min:8} {sl:14.{spec.digits}f} "
              f"{min_risk:9.2f} ({min_risk / acc.equity * 100:4.1f}%) -> {verdict}")
    broker.shutdown()


if __name__ == "__main__":
    main()
