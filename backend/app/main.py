import json
from datetime import date, timedelta
from functools import lru_cache
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.metrics import adjust_forecast, coverage, error_metrics, procurement_buffer, trailing_bias
from app.analysis.selection import cutoff_for, select_forecasts
from app.config import settings
from app.schemas import (
    BufferResponse,
    ForecastResponse,
    ForecastRow,
    Manifest,
    MetricsResponse,
    SnapshotMeta,
)

app = FastAPI(title="Wind Forecast Decision Portal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)

Cutoff = Annotated[str, Query(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="HH:MM UK time on D-1")]


def snapshot_ids() -> list[str]:
    return sorted(p.name for p in settings.snapshot_dir.glob("*") if (p / "manifest.json").is_file())


@lru_cache(maxsize=4)
def _read(snapshot_id: str):
    """Snapshots are immutable, so parsed data is cached per id. Callers must not mutate it."""
    path = settings.snapshot_dir / snapshot_id
    return (
        Manifest.model_validate_json((path / "manifest.json").read_text()),
        pd.read_parquet(path / "forecasts.parquet"),
        pd.read_parquet(path / "actuals.parquet"),
    )


def load_snapshot(snapshot_id: str | None = None):
    """Latest snapshot by default (pass an id to reproduce). The id must be a discovered snapshot."""
    ids = snapshot_ids()
    if not ids:
        raise HTTPException(503, "No data snapshot available. Run `make ingest`.")
    if snapshot_id is not None and snapshot_id not in ids:
        raise HTTPException(404, "Unknown snapshot")
    default = settings.snapshot_id or ids[-1]  # SNAPSHOT_ID pins the default; empty means newest
    if default not in ids:
        raise HTTPException(503, f"Pinned snapshot {default} is not available")
    return _read(snapshot_id or default)


@lru_cache(maxsize=4)
def _forecast_minutes(snapshot_id: str) -> frozenset[int]:
    """Minutes past the hour on which the snapshot's forecasts have targets (WINDFOR: {0})."""
    return frozenset(int(m) for m in _read(snapshot_id)[1]["target_time"].dt.minute.unique())


@lru_cache(maxsize=128)
def _scored(snapshot_id: str, start: date, end: date, cutoff: str) -> pd.DataFrame:
    _, forecasts, actuals = _read(snapshot_id)
    return select_forecasts(forecasts, start, end, cutoff).merge(actuals, on="target_time", how="left")


def _known_history(snapshot_id: str, delivery_day: date, cutoff: str) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Scored targets whose actual a buyer could already see at the decision time for `delivery_day`.

    Uses targets from the start of the period whose actual had been published by the cutoff on D-1
    (a half-hour's actual is published when it ends). Each past target is scored against the forecast
    that was available at its own cutoff. The first day of the period has no history, so it is empty.
    """
    first = date.fromisoformat(settings.period_start)
    decision = cutoff_for(delivery_day, cutoff)
    if delivery_day > first:
        sel = _scored(snapshot_id, first, delivery_day - timedelta(days=1), cutoff)
        return sel[sel["target_time"] + pd.Timedelta(minutes=30) <= decision], decision
    return _scored(snapshot_id, first, first, cutoff).iloc[0:0], decision


def check_days(*days: date) -> None:
    lo, hi = date.fromisoformat(settings.period_start), date.fromisoformat(settings.period_end)
    if any(not lo <= d <= hi for d in days):
        raise HTTPException(422, f"Dates must be within {lo} and {hi}")


def meta(manifest: Manifest) -> SnapshotMeta:
    return SnapshotMeta(snapshot_id=manifest.snapshot_id, fetched_at=manifest.fetched_at)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/forecast/{delivery_day}", response_model=ForecastResponse)
def forecast(delivery_day: date, cutoff: Cutoff = settings.default_cutoff, snapshot: str | None = None):
    check_days(delivery_day)
    manifest, _, _ = load_snapshot(snapshot)
    sel = _scored(manifest.snapshot_id, delivery_day, delivery_day, cutoff)
    history, _ = _known_history(manifest.snapshot_id, delivery_day, cutoff)
    bias = trailing_bias(history)
    sel = sel.assign(adjusted_mw=adjust_forecast(sel["forecast_mw"], bias))
    rows = [ForecastRow.model_validate(r) for r in json.loads(sel.to_json(orient="records", date_format="iso"))]
    return ForecastResponse(
        **meta(manifest).model_dump(),
        cutoff=cutoff_for(delivery_day, cutoff).to_pydatetime(),
        coverage=coverage(sel, _forecast_minutes(manifest.snapshot_id)),
        metrics=error_metrics(sel["forecast_mw"], sel["actual_mw"]),
        adjustment_mw=bias,
        adjusted_metrics=error_metrics(sel["adjusted_mw"], sel["actual_mw"]),
        rows=rows,
    )


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(
    start: date,
    end: date,
    quantile: Annotated[float, Query(ge=0, le=1)] = 0.9,
    cutoff: Cutoff = settings.default_cutoff,
    snapshot: str | None = None,
):
    if start > end:
        raise HTTPException(422, "start must not be after end")
    check_days(start, end)
    manifest, _, _ = load_snapshot(snapshot)
    sel = _scored(manifest.snapshot_id, start, end, cutoff)
    return MetricsResponse(
        **meta(manifest).model_dump(),
        coverage=coverage(sel, _forecast_minutes(manifest.snapshot_id)),
        metrics=error_metrics(sel["forecast_mw"], sel["actual_mw"]),
        buffer=procurement_buffer(sel["forecast_mw"], sel["actual_mw"], quantile),
    )


@app.get("/api/buffer/{delivery_day}", response_model=BufferResponse)
def trailing_buffer(
    delivery_day: date,
    quantile: Annotated[float, Query(ge=0, le=1)] = 0.9,
    cutoff: Cutoff = settings.default_cutoff,
    adjust: bool = False,
    snapshot: str | None = None,
):
    """Buffer for D from errors a buyer could already see at the decision time (see `_known_history`).

    With `adjust`, the mean error over that same history is removed from every forecast first, so the
    buffer covers what is left once a buyer has corrected for the level bias. The first day has no
    history, so n is 0 and nothing is adjusted.
    """
    check_days(delivery_day)
    manifest, _, _ = load_snapshot(snapshot)
    first = date.fromisoformat(settings.period_start)
    sel, decision = _known_history(manifest.snapshot_id, delivery_day, cutoff)
    bias = trailing_bias(sel)
    forecast_mw = adjust_forecast(sel["forecast_mw"], bias) if adjust else sel["forecast_mw"]
    return BufferResponse(
        **meta(manifest).model_dump(),
        basis="trailing",
        adjusted=adjust,
        adjustment_mw=bias if adjust else None,
        window_start=first,
        known_until=decision.to_pydatetime(),
        coverage=coverage(sel, _forecast_minutes(manifest.snapshot_id)),
        buffer=procurement_buffer(forecast_mw, sel["actual_mw"], quantile),
    )
