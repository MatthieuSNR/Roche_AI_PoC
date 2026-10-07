import sys
from pathlib import Path

from helpers import make_comments, make_snapshots
from roche_poc.stats.profile import build_profile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))


def test_charts_render_from_a_profile_without_streamlit():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "charts", Path(__file__).resolve().parents[1] / "dashboard" / "components" / "charts.py"
    )
    charts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(charts)
    p = build_profile(make_snapshots(), make_comments(), "vendor", "Vendor A")
    records = [{"Snapshot_Date": r["_snap"], "critical_share": r["critical_share"]}
               for r in p["history"]["critical_share_series"]]
    for fig in (
        charts.status_timeline_chart(p["history"]["status_timeline"]),
        charts.critical_share_chart(records, "stable"),
        charts.root_cause_chart(p["root_causes"]["table"]),
        charts.root_cause_chart([]),
    ):
        assert fig.axes
