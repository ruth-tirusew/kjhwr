"""Accuracy metrics, coverage and procurement buffer."""

import numpy as np
import pandas as pd


def _pairs(forecast: pd.Series, actual: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"f": forecast, "a": actual}).dropna()


def coverage(sel: pd.DataFrame, forecast_minutes: set[int]) -> dict:
    """How many half-hour targets could be scored, and the reasons the rest could not (never filled).

    `forecast_minutes` are the minutes past the hour on which the forecast dataset has targets at all
    (WINDFOR: only :00). Targets off that grid never had a forecast; `no_forecast` counts only
    on-grid targets with no forecast published by the cutoff. Reasons can overlap, so they need not sum.
    """
    f, a = sel["forecast_mw"], sel["actual_mw"]
    on_grid = sel["target_time"].dt.minute.isin(forecast_minutes)
    return {
        "targets": int(len(sel)),
        "scored": int(len(_pairs(f, a))),
        "off_forecast_grid": int((~on_grid).sum()),
        "no_forecast": int((f.isna() & on_grid).sum()),
        "no_actual": int(a.isna().sum()),
    }


def error_metrics(forecast: pd.Series, actual: pd.Series) -> dict:
    """Error = forecast - actual. Positive bias means over-forecast. Unscored targets are excluded;
    see `coverage` for how many. With nothing scored, every statistic is None."""
    pair = _pairs(forecast, actual)
    n = int(len(pair))
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "p50_abs": None, "p90_abs": None, "p95_abs": None}
    err = pair["f"] - pair["a"]
    abs_err = err.abs()
    return {
        "n": n,
        "mae": float(abs_err.mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),
        "p50_abs": float(abs_err.quantile(0.5)),
        "p90_abs": float(abs_err.quantile(0.9)),
        "p95_abs": float(abs_err.quantile(0.95)),
    }


def trailing_bias(sel: pd.DataFrame) -> float | None:
    """Mean error (forecast - actual) over the scored targets in `sel`; None when nothing was scored."""
    pair = _pairs(sel["forecast_mw"], sel["actual_mw"])
    return float((pair["f"] - pair["a"]).mean()) if len(pair) else None


def adjust_forecast(forecast: pd.Series, bias: float | None) -> pd.Series:
    """Remove a level bias from a forecast. Generation cannot be negative, so the result is floored at 0.
    With no bias to remove the forecast is returned unchanged."""
    return forecast if bias is None else (forecast - bias).clip(lower=0)


def procurement_buffer(forecast: pd.Series, actual: pd.Series, quantile: float = 0.9) -> dict:
    """Unconditional quantile of shortfall in MW, over all scored targets.

    Shortfall = max(forecast - actual, 0): the MW by which wind under-delivered against the forecast.
    Targets with no shortfall count as 0, so this is NOT "the P90 of the shortfalls that occurred".
    """
    pair = _pairs(forecast, actual)
    shortfall = (pair["f"] - pair["a"]).clip(lower=0)
    return {
        "quantile": quantile,
        "n": int(len(pair)),
        "n_shortfall": int((shortfall > 0).sum()),
        "buffer_mw": float(shortfall.quantile(quantile)) if len(pair) else None,
    }
