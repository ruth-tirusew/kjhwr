from datetime import date

import pandas as pd

from app.analysis.selection import select_forecasts


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_picks_latest_publish_at_or_before_cutoff():
    t = ts("2026-01-10 12:00")
    fc = pd.DataFrame(
        {
            "target_time": [t, t, t],
            "publish_time": [ts("2026-01-09 03:00"), ts("2026-01-09 09:00"), ts("2026-01-09 10:00")],
            "forecast_mw": [100.0, 200.0, 300.0],
        }
    )
    out = select_forecasts(fc, date(2026, 1, 10), date(2026, 1, 10))
    row = out[out["target_time"] == t].iloc[0]
    assert row["forecast_mw"] == 200.0  # boundary publish_time == cutoff is eligible
    assert row["publish_time"] == ts("2026-01-09 09:00")


def test_each_day_in_a_range_uses_its_own_cutoff():
    t1, t2 = ts("2026-01-10 12:00"), ts("2026-01-11 12:00")
    fc = pd.DataFrame(
        {
            "target_time": [t1, t2, t2],
            "publish_time": [ts("2026-01-09 08:00"), ts("2026-01-10 08:00"), ts("2026-01-10 10:00")],
            "forecast_mw": [1.0, 2.0, 3.0],
        }
    )
    out = select_forecasts(fc, date(2026, 1, 10), date(2026, 1, 11)).set_index("target_time")
    assert len(out) == 96
    assert out.loc[t1, "forecast_mw"] == 1.0
    assert out.loc[t2, "forecast_mw"] == 2.0  # 10:00 publish is after D-1 09:00


def test_missing_targets_stay_missing():
    out = select_forecasts(
        pd.DataFrame(
            {
                "target_time": pd.to_datetime([], utc=True),
                "publish_time": pd.to_datetime([], utc=True),
                "forecast_mw": pd.Series([], dtype=float),
            }
        ),
        date(2026, 1, 10),
        date(2026, 1, 10),
    )
    assert len(out) == 48
    assert out["forecast_mw"].isna().all()
