"""Elexon BMRS client. Used only at ingest time, never at request time."""

import httpx
import pandas as pd

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _stream(dataset: str, params: dict) -> pd.DataFrame:
    r = httpx.get(f"{BASE}/{dataset}/stream", params=params, timeout=120)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def fetch_actuals(start: str, end: str) -> pd.DataFrame:
    """FUELHH wind actuals by settlement date -> [target_time, actual_mw], half-hourly."""
    raw = _stream("FUELHH", {"settlementDateFrom": start, "settlementDateTo": end, "fuelType": "WIND"})
    return pd.DataFrame(
        {"target_time": pd.to_datetime(raw["startTime"], utc=True), "actual_mw": raw["generation"].astype(float)}
    ).sort_values("target_time", ignore_index=True)


def fetch_forecasts(start: str, end: str) -> pd.DataFrame:
    """WINDFOR forecasts by publish time -> [target_time, publish_time, forecast_mw].

    Note WINDFOR targets are hourly (on the hour), not half-hourly.
    `start` should precede the first delivery day by at least a day so D-1 publishes are included.
    """
    raw = _stream(
        "WINDFOR",
        {"publishDateTimeFrom": f"{start}T00:00:00Z", "publishDateTimeTo": f"{end}T23:59:59Z"},
    )
    return pd.DataFrame(
        {
            "target_time": pd.to_datetime(raw["startTime"], utc=True),
            "publish_time": pd.to_datetime(raw["publishTime"], utc=True),
            "forecast_mw": raw["generation"].astype(float),
        }
    ).sort_values(["target_time", "publish_time"], ignore_index=True)
