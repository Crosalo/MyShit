import numpy as np
import pandas as pd
import pytest

from research.ict import find_setups, simulate

# (high, low) je Kerze: Swing-Hoch bei 3, Swing-Tief bei 6, Sweep bei 10, BOS mit Lücke bei 12,
# Rücklauf ins Gap bei 14, danach Abverkauf bis unter das 2R-Ziel.
BARS = [(1.010, 1.000), (1.015, 1.005), (1.020, 1.010), (1.030, 1.020), (1.025, 1.012), (1.020, 1.008),
        (1.015, 1.002), (1.020, 1.006), (1.024, 1.010), (1.027, 1.015), (1.034, 1.020), (1.026, 1.012),
        (1.013, 0.998), (1.005, 0.995), (1.014, 1.000), (1.010, 0.990), (0.995, 0.975), (0.980, 0.965)]
CLOSES = {10: 1.025, 11: 1.013, 12: 0.999}


def frame(mirror=False):
    h = np.array([b[0] for b in BARS])
    l = np.array([b[1] for b in BARS])
    c = np.array([CLOSES.get(i, (h[i] + l[i]) / 2) for i in range(len(BARS))])
    o = c.copy()
    if mirror:  # an 2.0 gespiegelt: dasselbe Muster als Long
        h, l, c, o = 2 - l, 2 - h, 2 - c, 2 - o
    t = pd.date_range("2026-03-02 00:00", periods=len(BARS), freq="h", tz="UTC")
    return pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c})


@pytest.mark.parametrize("mirror,direction", [(False, -1), (True, 1)])
def test_sweep_bos_fvg_trade_hits_2r(mirror, direction):
    df = frame(mirror)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    setups = find_setups(o, h, l, c, direction)
    assert len(setups) == 1
    s = setups[0]
    assert s["bar"] == 12 and s["dir"] == direction
    assert abs(s["entry"] - s["stop"]) == pytest.approx(0.021)
    trades = simulate(df, np.zeros(len(df)), 0.0, setups)
    assert len(trades) == 1 and trades.iloc[0].reason == "TP"
    assert trades.iloc[0].r == pytest.approx(2.0)


def test_no_setup_without_sweep():
    df = frame()
    o, h, l, c = (df[k].to_numpy(copy=True) for k in ("open", "high", "low", "close"))
    h[10] = 1.029  # kein Stich über das Swing-Hoch
    assert find_setups(o, h, l, c, -1) == []
