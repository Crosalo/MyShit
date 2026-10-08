import json

import numpy as np
import pandas as pd
import pytest

from research.mt5_files import iter_mt5_files
from research.strategies import Context

CFG = {"risk": {"commission_per_lot": 4.5}}
POINT = 0.00001


def write_export(folder, n=6000, bar_spread=0, profile=None):
    start = int(pd.Timestamp("2026-07-06 10:00").timestamp())  # Serverzeit (UTC+3, Sommer)
    times = start + 60 * np.arange(n)
    pd.DataFrame({"time": times, "open": 1.1, "high": 1.1002, "low": 1.0998, "close": 1.1,
                  "spread": bar_spread}).to_csv(folder / "EURUSD_M1.csv", index=False)
    (folder / "EURUSD_spec.json").write_text(json.dumps({
        "symbol": "EURUSD", "path": "Forex\\EURUSD", "currency_profit": "USD", "point": POINT,
        "trade_tick_size": POINT, "trade_tick_value": 0.86, "trade_tick_value_loss": 0.86,
        "trade_contract_size": 100000.0, "volume_min": 0.01}))
    (folder / "meta.json").write_text(json.dumps({"server_offset_seconds": 3 * 3600, "server": "Test"}))
    if profile is not None:
        (folder / "spread_profile.json").write_text(json.dumps(
            {"EURUSD": {"symbol": "EURUSD", "point": POINT, "minutes": 1, "hourly_points": profile}}))


def test_server_time_to_utc_and_costs(tmp_path):
    write_export(tmp_path)
    inst, df, spread, src = next(iter_mt5_files(tmp_path, CFG, None))
    assert df["time"].iloc[0] == pd.Timestamp("2026-07-06 07:00", tz="UTC")
    assert inst.asset == "fx" and inst.minlot_value() == pytest.approx(0.01 * 0.86 / POINT)
    assert inst.commission_price == pytest.approx(4.5 / (0.86 / POINT))
    # ohne Spread-Profil: halber Annahme-Spread als Boden, weil der Bar-Spread 0 ist
    assert spread.min() == pytest.approx(0.00001) and src.startswith("Annahme")


def test_tick_profile_by_server_hour_beats_zero_bar_spread(tmp_path):
    profile = [1.0] * 24
    profile[10] = 7.0
    profile[11] = None  # fehlende Stunde -> Median
    write_export(tmp_path, profile=profile)
    _, _, spread, src = next(iter_mt5_files(tmp_path, CFG, None))
    assert src.startswith("Ticks")
    assert spread[0] == pytest.approx(7.0 * POINT)  # 10:00 Serverzeit
    assert spread[60] == pytest.approx(1.0 * POINT)  # 11:00 Serverzeit, Median der übrigen Stunden


def test_bar_spread_wins_when_wider(tmp_path):
    write_export(tmp_path, bar_spread=50, profile=[1.0] * 24)
    _, _, spread, _ = next(iter_mt5_files(tmp_path, CFG, None))
    assert np.all(spread == pytest.approx(50 * POINT))


def test_only_last_gapless_block_counts(tmp_path):
    write_export(tmp_path, n=12000)
    df = pd.read_csv(tmp_path / "EURUSD_M1.csv")
    df.loc[6000:, "time"] += 10 * 86400  # 10 Tage fehlende Historie
    df.to_csv(tmp_path / "EURUSD_M1.csv", index=False)
    _, out, _, _ = next(iter_mt5_files(tmp_path, CFG, None))
    assert len(out) == 6000


def test_m5_files_and_tf_min(tmp_path):
    write_export(tmp_path)
    df = pd.read_csv(tmp_path / "EURUSD_M1.csv")
    df["time"] = df["time"].iloc[0] + 300 * np.arange(len(df))
    df.to_csv(tmp_path / "EURUSD_M5.csv", index=False)
    inst, out, _, _ = next(iter_mt5_files(tmp_path, CFG, None, tf="M5"))
    assert Context(out, inst).tf_min == 5
