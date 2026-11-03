"""Compare two snapshots of the same window to detect post-publication revisions.

Usage: python -m app.ingest.diff <snapshot_a> <snapshot_b>
"""

import sys

import pandas as pd

from app.config import settings
from app.schemas import Manifest


def _load(snap_id: str):
    path = settings.snapshot_dir / snap_id
    manifest = Manifest.model_validate_json((path / "manifest.json").read_text())
    return manifest, pd.read_parquet(path / "forecasts.parquet"), pd.read_parquet(path / "actuals.parquet")


def diff_frames(a: pd.DataFrame, b: pd.DataFrame, key: list[str], value: str) -> dict:
    """Outer-join on key and classify rows: identical, changed, only in a, only in b."""
    m = a.merge(b, on=key, how="outer", suffixes=("_a", "_b"), indicator=True)
    both = m[m["_merge"] == "both"]
    delta = (both[f"{value}_b"] - both[f"{value}_a"]).abs()
    changed = both[delta > 0].assign(abs_diff=delta[delta > 0])
    return {
        "rows_a": len(a),
        "rows_b": len(b),
        "identical": int((delta == 0).sum()),
        "changed": changed,
        "only_in_a": m[m["_merge"] == "left_only"],
        "only_in_b": m[m["_merge"] == "right_only"],
    }


def report(a_id: str, b_id: str) -> bool:
    """Print a report; return True if any difference was found."""
    (ma, fa, aa), (mb, fb, ab) = _load(a_id), _load(b_id)
    print(f"A {ma.snapshot_id} fetched {ma.fetched_at}\nB {mb.snapshot_id} fetched {mb.fetched_at}")
    any_diff = False
    for name, (x, y, key, val) in {
        "WINDFOR forecasts": (fa, fb, ["target_time", "publish_time"], "forecast_mw"),
        "FUELHH actuals": (aa, ab, ["target_time"], "actual_mw"),
    }.items():
        d = diff_frames(x, y, key, val)
        n_ch, n_a, n_b = len(d["changed"]), len(d["only_in_a"]), len(d["only_in_b"])
        any_diff |= bool(n_ch or n_a or n_b)
        print(
            f"\n{name}: A={d['rows_a']} B={d['rows_b']} identical={d['identical']} "
            f"changed={n_ch} only_in_A={n_a} only_in_B={n_b}"
        )
        if n_ch:
            ch = d["changed"]
            print(f"  abs diff MW: max={ch['abs_diff'].max():.1f} mean={ch['abs_diff'].mean():.1f}")
            print(ch.sort_values("abs_diff", ascending=False).head(10).to_string(index=False))
    print("\nRESULT:", "DIFFERENCES FOUND" if any_diff else "no differences")
    return any_diff


if __name__ == "__main__":
    sys.exit(1 if report(sys.argv[1], sys.argv[2]) else 0)
