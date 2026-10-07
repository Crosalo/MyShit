"""Backtest mit derselben Strategie-, Risiko- und Sitzungslogik wie live.

python -m bot.backtest --csv data/EURUSD_M15.csv --spec data/EURUSD_spec.json --equity 19

Annahmen (bewusst pessimistisch):
- Kerzen sind Bid-Kurse; Käufe zahlen Bid + Spread, Short-Exits ebenso.
- Werden SL und TP in derselben Kerze berührt, zählt der SL.
- Kurslücken über den SL hinweg werden zum (schlechteren) Eröffnungskurs gefüllt.
- Historische News sind NICHT enthalten (der Kalender-Feed hat nur die aktuelle Woche).
"""
import argparse
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import load_config
from .risk import SymbolSpec, position_size
from .session import in_trade_window, must_be_flat
from .strategy import TrendPullback

# Grobe Standardwerte (Kontowährung ~ USD), falls keine Spec aus MT5 exportiert wurde.
DEFAULT_SPECS = {
    "EURUSD": dict(point=0.00001, digits=5, tick_size=0.00001, tick_value=1.0, spread=0.00002),
    "GBPUSD": dict(point=0.00001, digits=5, tick_size=0.00001, tick_value=1.0, spread=0.00004),
    "AUDUSD": dict(point=0.00001, digits=5, tick_size=0.00001, tick_value=1.0, spread=0.00003),
    "USDJPY": dict(point=0.001, digits=3, tick_size=0.001, tick_value=0.67, spread=0.003),
    "XAUUSD": dict(point=0.01, digits=2, tick_size=0.01, tick_value=1.0, spread=0.12),
}


@dataclass
class Trade:
    side: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    lots: float
    pnl: float
    r_multiple: float
    exit_reason: str


@dataclass
class BacktestResult:
    start_equity: float
    final_equity: float
    trades: list = field(default_factory=list)
    skipped: int = 0
    skip_reason: str = ""
    max_drawdown_pct: float = 0.0

    def summary(self) -> dict:
        pnls = np.array([t.pnl for t in self.trades])
        wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
        return {
            "trades": len(self.trades),
            "uebersprungen_mindestlot": self.skipped,
            "trefferquote_pct": round(len(wins) / len(pnls) * 100, 1) if len(pnls) else 0.0,
            "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else None,
            "avg_r": round(float(np.mean([t.r_multiple for t in self.trades])), 3) if self.trades else 0.0,
            "start_equity": round(self.start_equity, 2),
            "end_equity": round(self.final_equity, 2),
            "rendite_pct": round((self.final_equity / self.start_equity - 1) * 100, 1),
            "max_drawdown_pct": round(self.max_drawdown_pct, 1),
        }


def run_backtest(df: pd.DataFrame, spec: SymbolSpec, cfg: dict, start_equity: float,
                 spread: float | None = None) -> BacktestResult:
    strategy = TrendPullback(cfg["strategy"])
    risk, session = cfg["risk"], cfg["session"]
    commission = risk["commission_per_lot"]
    d = strategy.prepare(df.reset_index(drop=True))
    times = list(pd.to_datetime(d["time"], utc=True))
    o, h, l = d["open"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy()
    if spread is not None:
        sp = np.full(len(d), spread)
    elif "spread" in d:
        sp = d["spread"].to_numpy() * spec.point
    else:
        raise ValueError("Spread fehlt: --spread angeben oder Spalte 'spread' liefern")
    long_sig, short_sig = d["long_sig"].to_numpy(), d["short_sig"].to_numpy()

    res = BacktestResult(start_equity, start_equity)
    equity = peak = start_equity
    pos = None
    day, day_start, trades_today, halted = None, start_equity, 0, False

    def close(i, price, reason):
        nonlocal equity, peak, pos, halted
        direction = 1 if pos["side"] == "buy" else -1
        pnl = (price - pos["entry"]) * direction / spec.tick_size * spec.tick_value * pos["lots"]
        pnl -= commission * pos["lots"]
        equity += pnl
        res.trades.append(Trade(pos["side"], pos["time"], times[i], pos["entry"], price,
                                pos["lots"], pnl, pnl / pos["risk"], reason))
        peak = max(peak, equity)
        res.max_drawdown_pct = max(res.max_drawdown_pct, (peak - equity) / peak * 100)
        if (day_start - equity) / day_start * 100 >= risk["max_daily_loss_pct"]:
            halted = True
        pos = None

    for i in range(strategy.min_bars, len(d) - 1):
        if times[i].date() != day:
            day, day_start, trades_today, halted = times[i].date(), equity, 0, False

        if pos is not None:
            if must_be_flat(times[i], session):
                close(i, o[i] + (sp[i] if pos["side"] == "sell" else 0), "Handelsende")
            elif pos["side"] == "buy":
                if l[i] <= pos["sl"]:
                    close(i, min(o[i], pos["sl"]), "SL")
                elif h[i] >= pos["tp"]:
                    close(i, pos["tp"], "TP")
            else:
                if h[i] + sp[i] >= pos["sl"]:
                    close(i, max(o[i] + sp[i], pos["sl"]), "SL")
                elif l[i] + sp[i] <= pos["tp"]:
                    close(i, pos["tp"], "TP")

        if equity <= 0:
            break
        if pos is not None or halted or trades_today >= risk["max_trades_per_day"]:
            continue
        if not (long_sig[i] or short_sig[i]) or not in_trade_window(times[i + 1], session):
            continue
        sig = strategy.signal_at(d, i)
        size = position_size(equity, risk["risk_per_trade_pct"], sig.sl_distance, spec, commission)
        if size.lots <= 0:
            res.skipped += 1
            res.skip_reason = size.reason
            continue
        if sig.side == "buy":
            entry = o[i + 1] + sp[i + 1]
            sl, tp = entry - sig.sl_distance, entry + sig.tp_distance
        else:
            entry = o[i + 1]
            sl, tp = entry + sig.sl_distance, entry - sig.tp_distance
        pos = dict(side=sig.side, entry=entry, sl=sl, tp=tp, lots=size.lots,
                   risk=size.risk_money, time=times[i + 1])
        trades_today += 1

    if pos is not None:
        close(len(d) - 1, d["close"].iloc[-1], "Datenende")
    res.final_equity = equity
    return res


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    if pd.api.types.is_numeric_dtype(df["time"]):
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    else:
        df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def load_spec(symbol: str, spec_path: str | None) -> tuple[SymbolSpec, float | None]:
    if spec_path:
        with open(spec_path, encoding="utf-8") as f:
            return SymbolSpec(**json.load(f)), None
    base = DEFAULT_SPECS[symbol]
    spec = SymbolSpec(name=symbol, volume_min=0.01, volume_max=100, volume_step=0.01,
                      **{k: v for k, v in base.items() if k != "spread"})
    return spec, base["spread"]


def main(argv=None):
    p = argparse.ArgumentParser(description="Backtest der Bot-Strategie")
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--spec", help="Spec-JSON aus export_history (genauer als Standardwerte)")
    p.add_argument("--equity", type=float, default=1000.0)
    p.add_argument("--spread", type=float, help="fester Spread in Preis-Einheiten")
    p.add_argument("--config", default=None)
    p.add_argument("--trades", action="store_true", help="einzelne Trades ausgeben")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    spec, default_spread = load_spec(args.symbol, args.spec)
    spread = args.spread if args.spread is not None else default_spread
    result = run_backtest(load_csv(args.csv), spec, cfg, args.equity, spread)
    for key, value in result.summary().items():
        print(f"{key:>26}: {value}")
    if result.skipped:
        print(f"\nBeispiel Ablehnung: {result.skip_reason}")
    if args.trades:
        for t in result.trades:
            print(f"{t.entry_time:%Y-%m-%d %H:%M} {t.side:4} {t.lots:5} {t.exit_reason:12} {t.pnl:8.2f} ({t.r_multiple:+.2f}R)")


if __name__ == "__main__":
    main()
