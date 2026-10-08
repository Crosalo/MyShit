import numpy as np
import pandas as pd
import pytest

from research.break_retest import break_retest
from research.instruments import BY_NAME
from research.strategies import Context

# M1-Kerzen ab 9:25 New York (13:25 UTC, Sommerzeit): (open, high, low, close)
DAY = [(100.5, 100.6, 100.4, 100.5)] * 5 + [  # 9:25-9:29 vor der Eröffnung
    (100.5, 101.0, 100.0, 100.8), (100.8, 100.9, 100.3, 100.4), (100.4, 100.7, 100.2, 100.6),
    (100.6, 100.9, 100.5, 100.7), (100.7, 100.8, 100.1, 100.3),  # 9:30-9:34 Range 100.0-101.0
    (100.3, 101.6, 100.3, 101.5),  # 9:35 Ausbruch nach oben
    (101.5, 101.5, 100.9, 101.2),  # 9:36 Retest berührt 101.0 (rot)
    (101.1, 101.7, 101.0, 101.6),  # 9:37 grün über dem Level -> Long
] + [(101.6, 101.7, 101.5, 101.6)] * 10


def ctx(rows):
    o, h, l, c = (np.array([r[i] for r in rows]) for i in range(4))
    t = pd.date_range("2026-07-07 13:25", periods=len(rows), freq="min", tz="UTC")
    return Context(pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c}), BY_NAME["US500"])


def test_long_after_break_and_retest():
    sig = break_retest(ctx(DAY))
    assert np.flatnonzero(sig.long).tolist() == [12] and not sig.short.any()
    assert sig.sl_dist[12] == pytest.approx(101.6 - 100.9)
    assert sig.tp_dist[12] == pytest.approx(2 * (101.6 - 100.9))


def test_close_back_in_range_invalidates():
    rows = list(DAY)
    rows[11] = (101.5, 101.5, 100.9, 100.95)  # Retest-Kerze schließt in der Range
    sig = break_retest(ctx(rows))
    assert not sig.long[12]
