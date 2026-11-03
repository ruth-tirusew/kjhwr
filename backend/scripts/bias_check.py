"""Is the forecast-vs-actual gap a level offset, or a timing/join problem?

Usage (from backend/): python -m scripts.bias_check [snapshot_id]
Scores every January half-hour as the API does, then reports ratio, best scalar fit, time-shift sensitivity
and bias by hour, week and wind level.
"""

import sys
from datetime import date

import pandas as pd

from app.analysis.selection import select_forecasts
from app.config import settings


def main(snapshot_id: str | None = None) -> None:
    ids = sorted(p.name for p in settings.snapshot_dir.glob("*") if (p / "manifest.json").is_file())
    path = settings.snapshot_dir / (snapshot_id or ids[-1])
    fc, ac = pd.read_parquet(path / "forecasts.parquet"), pd.read_parquet(path / "actuals.parquet")
    print(f"snapshot {path.name}")
    print("forecast target minutes:", sorted(int(m) for m in fc.target_time.dt.minute.unique()))
    print("actual target minutes:  ", sorted(int(m) for m in ac.target_time.dt.minute.unique()))

    sel = select_forecasts(fc, date(2026, 1, 1), date(2026, 1, 31)).merge(ac, on="target_time", how="left")
    sel = sel.dropna(subset=["forecast_mw", "actual_mw"])
    sel["err"] = sel.forecast_mw - sel.actual_mw
    f, a = sel.forecast_mw, sel.actual_mw
    print(f"\nscored n={len(sel)}  mean forecast={f.mean():.0f}  mean actual={a.mean():.0f}")
    print(f"ratio of means={f.mean() / a.mean():.3f}  median(f/a)={(f / a).median():.3f}  corr={f.corr(a):.3f}")
    print(f"over-forecast share={(sel.err > 0).mean():.1%}")
    k = (f * a).sum() / (f**2).sum()
    print(f"best scalar a = {k:.3f} * f: MAE {(a - k * f).abs().mean():.0f} vs raw {sel.err.abs().mean():.0f}")

    print("\nforecast(t) vs actual(t + lag half-hours): lag, MAE, bias")
    actual = ac.set_index("target_time").actual_mw
    fcast = sel.set_index("target_time").forecast_mw
    for lag in range(-8, 9, 4):
        shifted = actual.copy()
        shifted.index = shifted.index - pd.Timedelta(minutes=30 * lag)
        j = pd.concat([fcast, shifted], axis=1, keys=["f", "a"], join="inner").dropna()
        print(f"{lag:+3d}  {(j.f - j.a).abs().mean():7.0f}  {(j.f - j.a).mean():7.0f}")

    print("\nbias by hour:", sel.groupby(sel.target_time.dt.hour).err.mean().round(0).astype(int).to_dict())
    week = sel.target_time.dt.isocalendar().week
    print("bias by ISO week:", sel.groupby(week).err.mean().round(0).astype(int).to_dict())
    tercile = pd.qcut(a, 3, labels=["low", "mid", "high"])
    print("bias by wind tercile:", sel.groupby(tercile, observed=True).err.mean().round(0).astype(int).to_dict())
    last = fc.sort_values("publish_time").groupby("target_time").last().reset_index().merge(ac, on="target_time")
    print(f"latest forecast ever published per target: bias={(last.forecast_mw - last.actual_mw).mean():.0f}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
