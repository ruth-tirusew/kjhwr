"""Pydantic models for the snapshot manifest and API payloads."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class SnapshotMeta(BaseModel):
    """Identifies the data behind a result."""

    snapshot_id: str
    fetched_at: datetime


class Manifest(SnapshotMeta):
    rows: dict[str, int]


class ForecastRow(BaseModel):
    target_time: datetime
    publish_time: datetime | None = None  # None = no eligible forecast
    forecast_mw: float | None = None
    adjusted_mw: float | None = None  # forecast_mw minus the bias known at the cutoff; None without a forecast
    actual_mw: float | None = None


class Coverage(BaseModel):
    """Half-hour targets in scope and how many could be scored. Unscored targets are never filled.

    The reasons can overlap, so they need not sum to `targets - scored`.
    """

    targets: int
    scored: int  # has both a forecast and an actual
    off_forecast_grid: int  # the forecast dataset never has targets here (WINDFOR is hourly: the :30s)
    no_forecast: int  # on the forecast grid, but nothing published by the cutoff
    no_actual: int


class ErrorMetrics(BaseModel):
    n: int
    mae: float | None  # None when nothing could be scored
    rmse: float | None
    bias: float | None
    p50_abs: float | None
    p90_abs: float | None
    p95_abs: float | None


class Buffer(BaseModel):
    quantile: float = Field(ge=0, le=1)
    n: int
    n_shortfall: int  # scored half-hours where wind under-delivered (shortfall > 0)
    buffer_mw: float | None


class ForecastResponse(SnapshotMeta):
    cutoff: datetime
    coverage: Coverage
    metrics: ErrorMetrics  # this delivery day only
    adjustment_mw: float | None  # mean error known at the cutoff, removed from adjusted_mw; None without history
    adjusted_metrics: ErrorMetrics  # this delivery day only, using adjusted_mw
    rows: list[ForecastRow]


class MetricsResponse(SnapshotMeta):
    """Retrospective evaluation over a date range. Includes days after any one delivery day."""

    coverage: Coverage
    metrics: ErrorMetrics
    buffer: Buffer


class BufferResponse(SnapshotMeta):
    """Buffer from errors already known at the decision time (no look-ahead)."""

    basis: str
    adjusted: bool  # True: the forecast and its errors had `adjustment_mw` removed before the buffer was computed
    adjustment_mw: float | None
    window_start: date
    known_until: datetime  # the decision time: only targets whose actuals were published by then count
    coverage: Coverage
    buffer: Buffer
