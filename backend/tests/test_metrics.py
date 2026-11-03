import math

import pandas as pd
import pytest

from app.analysis.metrics import error_metrics, procurement_buffer


def test_error_metrics_hand_fixture():
    f = pd.Series([110.0, 90.0, 100.0, None])
    a = pd.Series([100.0, 100.0, 100.0, 50.0])
    m = error_metrics(f, a)
    assert m["n"] == 3  # missing forecast dropped, not filled
    assert m["mae"] == 20 / 3
    assert math.isclose(m["rmse"], math.sqrt(200 / 3))
    assert m["bias"] == 0.0


def test_buffer_only_counts_over_forecast_shortfall():
    f = pd.Series([110.0, 90.0, 100.0])
    a = pd.Series([100.0, 100.0, 100.0])
    # shortfall (forecast - actual, floored): [10, 0, 0]
    assert procurement_buffer(f, a, 1.0)["buffer_mw"] == 10.0


def test_coverage_separates_forecast_grid_from_missing():
    from app.analysis.metrics import coverage

    t = pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:30", "2026-01-01 01:00", "2026-01-01 01:30"], utc=True)
    sel = pd.DataFrame({"target_time": t, "forecast_mw": [1.0, None, None, None], "actual_mw": [1.0, 2.0, None, 4.0]})
    # forecasts only exist on the hour: 00:30 and 01:30 are off-grid, 01:00 is a real miss
    assert coverage(sel, {0}) == {
        "targets": 4,
        "scored": 1,
        "off_forecast_grid": 2,
        "no_forecast": 1,
        "no_actual": 1,
    }


def test_buffer_is_unconditional_and_counts_zeros():
    f = pd.Series([110.0] + [100.0] * 9)
    a = pd.Series([100.0] * 10)
    b = procurement_buffer(f, a, 0.9)
    assert b["n_shortfall"] == 1
    assert b["buffer_mw"] == pytest.approx(1.0)  # 0.9 quantile of [0]*9+[10] interpolates between 0 and 10, not 10


def test_nothing_scored_gives_none_not_nan():
    empty = pd.Series([None, None], dtype=float)
    assert error_metrics(empty, empty)["mae"] is None
    assert procurement_buffer(empty, empty)["buffer_mw"] is None


def test_trailing_bias_and_adjustment():
    from app.analysis.metrics import adjust_forecast, trailing_bias

    sel = pd.DataFrame({"forecast_mw": [110.0, 120.0, None], "actual_mw": [100.0, 100.0, 100.0]})
    assert trailing_bias(sel) == 15.0  # unscored rows are ignored
    assert trailing_bias(sel.iloc[0:0]) is None
    adjusted = adjust_forecast(pd.Series([110.0, 5.0]), 15.0)
    assert list(adjusted) == [95.0, 0.0]  # floored at zero: generation cannot be negative
    assert list(adjust_forecast(pd.Series([110.0]), None)) == [110.0]
