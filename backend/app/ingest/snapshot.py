"""Fetch Elexon data once and freeze it as a named snapshot with a fetch time."""

from datetime import UTC, datetime

import pandas as pd

from app.config import settings
from app.ingest import elexon
from app.schemas import Manifest


def main() -> None:
    fetched = datetime.now(UTC)
    snap_id = fetched.strftime("%Y%m%dT%H%M%SZ")
    out = settings.snapshot_dir / snap_id
    out.mkdir(parents=True, exist_ok=False)

    actuals = elexon.fetch_actuals(settings.period_start, settings.period_end)
    # Start forecasts a day early so D-1 publishes for 1 Jan are included.
    day_before = (pd.Timestamp(settings.period_start) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    forecasts = elexon.fetch_forecasts(day_before, settings.period_end)
    actuals.to_parquet(out / "actuals.parquet")
    forecasts.to_parquet(out / "forecasts.parquet")

    manifest = Manifest(
        snapshot_id=snap_id,
        fetched_at=fetched,
        rows={"actuals": len(actuals), "forecasts": len(forecasts)},
    )
    (out / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    print(f"wrote snapshot {snap_id}")


if __name__ == "__main__":
    main()
