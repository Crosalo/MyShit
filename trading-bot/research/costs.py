"""Kostenzerlegung: dieselben Trades vor Kosten, mit halbem Spread und mit vollen Kosten.

Zeigt, ob eine Strategie an den Kosten scheitert oder schon vor Kosten keinen Vorteil hat.
python -m research.costs --tf 15
"""
import argparse
from pathlib import Path

import numpy as np

from .data import load_histdata, spread_array
from .engine import Signals, force_exit_mask, simulate
from .instruments import UNIVERSE
from .strategies import STRATEGIES, TF_PARAMS, Context
from .timeframes import resample, to_m1

SCENARIOS = (("vor_kosten", 0.0, False), ("halber_spread", 0.5, True), ("volle_kosten", 1.0, True))


def breakdown(tf: int, data: Path, min_cost_ratio: float = 5.0) -> dict:
    res = {name: {s[0]: [] for s in SCENARIOS} for name in STRATEGIES}
    for inst in UNIVERSE:
        m1 = load_histdata(inst, data / "histdata", data / "m1" / f"{inst.name}.pkl")
        if m1 is None:
            continue
        spread, _ = spread_array(m1, inst, data / "spreads.json")
        bars = resample(m1, tf)
        ctx = Context(bars, inst)
        o, h, l, c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        fx = force_exit_mask(m1["time"])
        comm = inst.commission_price
        nxt = np.roll(spread, -1)
        for name, fn in STRATEGIES.items():
            sig = to_m1(fn(ctx, **TF_PARAMS[tf].get(name, {})), bars["time"], m1["time"], tf)
            keep = sig.sl_dist >= min_cost_ratio * (nxt + comm)  # gleiche Auswahl wie im echten Test
            sel = Signals(sig.long & keep, sig.short & keep, sig.sl_dist, sig.tp_dist, sig.max_hold)
            for label, mult, with_comm in SCENARIOS:
                t, _ = simulate(o, h, l, c, spread * mult, fx, sel, comm if with_comm else 0.0, min_cost_ratio=0)
                res[name][label].append(t["r"].to_numpy())
    return {name: {k: np.concatenate(v) if v else np.array([]) for k, v in d.items()} for name, d in res.items()}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--tf", type=int, default=1)
    p.add_argument("--data", default="data")
    args = p.parse_args(argv)
    res = breakdown(args.tf, Path(args.data))
    print("| Strategie | Trades | vor Kosten | halber Spread | volle Kosten |")
    print("|---|---|---|---|---|")
    for name, d in res.items():
        g, h, n = d["vor_kosten"], d["halber_spread"], d["volle_kosten"]
        if len(n):
            print(f"| {name} | {len(n)} | {g.mean():+.3f} | {h.mean():+.3f} | {n.mean():+.3f} |")


if __name__ == "__main__":
    main()
