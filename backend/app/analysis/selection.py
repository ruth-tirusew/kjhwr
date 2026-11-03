"""Decision-time forecast selection."""

from datetime import date

import pandas as pd


def _hhmm(hhmm: str) -> pd.Timedelta:
    h, m = map(int, hhmm.split(":"))
    return pd.Timedelta(hours=h, minutes=m)


def cutoff_for(delivery_day: date, hhmm: str = "09:00") -> pd.Timestamp:
    """Cutoff on D-1 at hhmm UK time. January is GMT so UTC == UK."""
    return pd.Timestamp(delivery_day, tz="UTC") - pd.Timedelta(days=1) + _hhmm(hhmm)


def select_forecasts(forecasts: pd.DataFrame, start: date, end: date, hhmm: str = "09:00") -> pd.DataFrame:
    """Latest forecast per half-hour target with publish_time <= cutoff of that target's delivery day.

    Covers every half-hour from `start` to `end` inclusive in one vectorised pass. Targets with no
    eligible forecast have NaN forecast_mw / publish_time (never filled).
    """
    first = pd.Timestamp(start, tz="UTC")
    targets = pd.date_range(first, pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=30), freq="30min")
    f = forecasts[forecasts["target_time"].isin(targets)].copy()
    f["cutoff"] = f["target_time"].dt.normalize() - pd.Timedelta(days=1) + _hhmm(hhmm)
    latest = (
        f[f["publish_time"] <= f["cutoff"]]
        .sort_values("publish_time")
        .groupby("target_time", as_index=False)
        .last()[["target_time", "publish_time", "forecast_mw"]]
    )
    return pd.DataFrame({"target_time": targets}).merge(latest, on="target_time", how="left")
