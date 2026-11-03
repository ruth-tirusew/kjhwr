import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Settings, settings
from app.schemas import Manifest


@pytest.fixture
def client(tmp_path, monkeypatch):
    snap = tmp_path / "20260101T000000Z"
    snap.mkdir()
    t = pd.date_range("2026-01-10", periods=48, freq="30min", tz="UTC")
    pd.DataFrame(
        {"target_time": t[::2], "publish_time": pd.Timestamp("2026-01-09 08:00", tz="UTC"), "forecast_mw": 100.0}
    ).to_parquet(snap / "forecasts.parquet")
    pd.DataFrame({"target_time": t, "actual_mw": 90.0}).to_parquet(snap / "actuals.parquet")
    (snap / "manifest.json").write_text(
        Manifest(snapshot_id=snap.name, fetched_at="2026-01-01T00:00:00Z", rows={}).model_dump_json()
    )
    (tmp_path.parent / "secret").mkdir(exist_ok=True)
    monkeypatch.setattr(settings, "snapshot_dir", tmp_path)
    main._read.cache_clear()
    main._scored.cache_clear()
    return TestClient(main.app)


def test_reports_coverage_for_a_day(client):
    body = client.get("/api/forecast/2026-01-10").json()
    assert body["coverage"] == {
        "targets": 48,
        "scored": 24,
        "off_forecast_grid": 24,
        "no_forecast": 0,
        "no_actual": 0,
    }
    assert body["metrics"]["n"] == 24 and body["metrics"]["bias"] == 10.0


def test_snapshot_id_must_be_discovered(client):
    assert client.get("/api/metrics?start=2026-01-10&end=2026-01-10&snapshot=../secret").status_code == 404
    assert client.get("/api/metrics?start=2026-01-10&end=2026-01-10&snapshot=20260101T000000Z").status_code == 200


@pytest.mark.parametrize(
    "qs",
    [
        "start=2026-01-10&end=2026-01-10&quantile=1.5",
        "start=2026-01-11&end=2026-01-10",
        "start=nonsense&end=2026-01-10",
        "start=2026-01-10&end=2026-01-10&cutoff=25:99",
        "start=2025-12-01&end=2026-01-10",
    ],
)
def test_bad_input_is_422(client, qs):
    assert client.get(f"/api/metrics?{qs}").status_code == 422


def test_bad_delivery_day_is_422(client):
    assert client.get("/api/forecast/not-a-date").status_code == 422


def test_pinned_snapshot_must_exist(client, monkeypatch):
    monkeypatch.setattr(settings, "snapshot_id", "20990101T000000Z")
    assert client.get("/api/metrics?start=2026-01-10&end=2026-01-10").status_code == 503
    monkeypatch.setattr(settings, "snapshot_id", "20260101T000000Z")
    assert client.get("/api/metrics?start=2026-01-10&end=2026-01-10").status_code == 200


def test_cors_origins_are_trimmed():
    assert Settings(cors_origins=" http://a.test , http://b.test ,").cors_origin_list == [
        "http://a.test",
        "http://b.test",
    ]


def test_trailing_buffer_uses_only_errors_known_at_decision(client):
    # Fixture: forecast 100 vs actual 90 on every on-the-hour target of 2026-01-10, so every shortfall is 10 MW.
    b = client.get("/api/buffer/2026-01-11").json()
    assert b["basis"] == "trailing"
    assert b["known_until"].startswith("2026-01-10T09:00")  # decision time for delivery day 11 Jan
    assert b["buffer"]["n"] == 9  # only 10 Jan targets that had ended by 09:00 (00:00 to 08:00 on the hour)
    assert b["buffer"]["buffer_mw"] == 10.0
    # One day later the whole of 10 Jan is known.
    assert client.get("/api/buffer/2026-01-12").json()["buffer"]["n"] == 24


def test_trailing_buffer_first_day_has_no_history(client):
    b = client.get("/api/buffer/2026-01-01").json()
    assert b["buffer"]["n"] == 0 and b["buffer"]["buffer_mw"] is None and b["coverage"]["targets"] == 0


def test_adjusted_buffer_removes_the_bias_known_at_decision(client):
    # Forecast is 10 MW high on every known target, so removing that bias leaves nothing to cover.
    raw = client.get("/api/buffer/2026-01-11").json()
    adj = client.get("/api/buffer/2026-01-11?adjust=true").json()
    assert raw["adjusted"] is False and raw["adjustment_mw"] is None
    assert adj["adjusted"] is True and adj["adjustment_mw"] == 10.0
    assert adj["buffer"]["buffer_mw"] == 0.0 and adj["buffer"]["n_shortfall"] == 0
    assert adj["buffer"]["n"] == raw["buffer"]["n"]


def test_adjusted_buffer_first_day_is_unadjusted(client):
    b = client.get("/api/buffer/2026-01-01?adjust=true").json()
    assert b["adjusted"] is True and b["adjustment_mw"] is None and b["buffer"]["buffer_mw"] is None


def test_forecast_rows_carry_the_adjusted_forecast(client):
    body = client.get("/api/forecast/2026-01-11").json()
    assert body["adjustment_mw"] == 10.0
    forecasts = [r for r in body["rows"] if r["forecast_mw"] is not None]
    assert forecasts == [] or all(r["adjusted_mw"] == r["forecast_mw"] - 10.0 for r in forecasts)
    assert all(r["adjusted_mw"] is None for r in body["rows"] if r["forecast_mw"] is None)
    assert body["adjusted_metrics"]["n"] == body["metrics"]["n"]


def test_first_day_forecast_has_no_adjustment(client):
    body = client.get("/api/forecast/2026-01-10").json()  # fixture data is for 10 Jan; 1 Jan history is empty
    assert body["adjustment_mw"] is None
    assert all(r["adjusted_mw"] == r["forecast_mw"] for r in body["rows"])
