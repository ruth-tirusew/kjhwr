import pandas as pd

from app.ingest.diff import diff_frames


def test_diff_classifies_rows():
    t = pd.to_datetime(["2026-01-01 00:00", "2026-01-01 01:00", "2026-01-01 02:00"], utc=True)
    a = pd.DataFrame({"target_time": t[:2], "actual_mw": [100.0, 200.0]})
    b = pd.DataFrame({"target_time": t[[0, 1, 2]], "actual_mw": [100.0, 210.0, 300.0]})
    d = diff_frames(a, b, ["target_time"], "actual_mw")
    assert d["identical"] == 1
    assert d["changed"]["abs_diff"].tolist() == [10.0]
    assert len(d["only_in_b"]) == 1 and len(d["only_in_a"]) == 0
