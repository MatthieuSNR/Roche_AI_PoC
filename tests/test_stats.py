import math

import pandas as pd

from helpers import SNAPSHOTS, make_comments, make_snapshots
from roche_poc import config
from roche_poc.stats import kpis, persistence, profile, trends, watchlist


def test_status_counts_latest_snapshot():
    now = kpis.latest_rows(make_snapshots())
    counts = kpis.status_counts(now)
    # latest: M1 Actual, M2 Potential, M3 Good, M4 Below, M5 Potential (M6 absent)
    assert counts == {"Good Part": 1, "Below Safety": 1, "Potential Stock Out": 2, "Actual Stock Out": 1}


def test_status_timeline_has_all_statuses_and_snapshots():
    tl = kpis.status_timeline(make_snapshots())
    assert list(tl.columns) == config.STATUS_ORDER
    assert len(tl) == 8
    assert tl.loc[SNAPSHOTS[0], "Actual Stock Out"] == 2  # materials 1 and 6


def test_critical_share_is_not_distorted_by_missing_rows():
    series = kpis.critical_share_timeline(make_snapshots())
    assert math.isclose(series.iloc[-1], 3 / 5)


def test_root_cause_percentages_use_known_denominator():
    table = kpis.root_cause_table(make_snapshots())
    assert math.isclose(table["pct_of_known"].sum(), 100.0, abs_tol=0.2)
    assert "S_Lack of Raw Material" in set(table[config.COL_ROOT_CAUSE])


def test_root_cause_coverage_flags_missing_cause():
    coverage = kpis.root_cause_coverage(kpis.latest_rows(make_snapshots()))
    assert coverage["critical_rows"] == 3
    assert coverage["with_root_cause"] == 2
    assert coverage["missing_pct"] == 33.3


def test_critical_streaks():
    s = persistence.critical_streaks(make_snapshots())
    assert s.loc[1, "current_streak"] == 8 and s.loc[1, "episodes"] == 1
    assert s.loc[2, "current_streak"] == 1 and s.loc[2, "episodes"] == 3
    assert s.loc[2, "n_critical_snapshots"] == 5
    assert s.loc[3, "n_critical_snapshots"] == 0 and s.loc[4, "n_critical_snapshots"] == 0
    assert s.loc[5, "current_streak"] == 2
    assert s.loc[6, "current_streak"] == 0 and s.loc[6, "n_critical_snapshots"] == 3


def test_trend_label_needs_enough_points_and_detects_direction():
    assert trends.trend_label([1, 2]) == "insufficient data"
    assert trends.trend_label([1, 2, 3, 4, 5, 6]) == "rising"
    assert trends.trend_label([6, 5, 4, 3, 2, 1]) == "falling"
    assert trends.trend_label([5, 5, 5, 5, 5]) == "stable"


def test_watchlist_rules_fire_on_the_expected_materials():
    wl = watchlist.build_watchlist(make_snapshots())
    by_rule = {rule: set(g[config.COL_MATERIAL]) for rule, g in wl.groupby("rule")}
    assert by_rule[watchlist.RULE_ESCALATE] == {1}
    assert by_rule[watchlist.RULE_NO_ROOT_CAUSE] == {1}
    assert by_rule[watchlist.RULE_NO_COMMENT] == {1}
    assert by_rule[watchlist.RULE_PERSISTENT] == {1}
    assert by_rule[watchlist.RULE_RECURRENT] == {2}
    assert by_rule[watchlist.RULE_LONG_DELAY] == {5}
    assert 3 not in set(wl[config.COL_MATERIAL]) and 6 not in set(wl[config.COL_MATERIAL])
    assert wl.iloc[0]["severity"] == watchlist.HIGH  # most severe first


def test_rank_entities_puts_riskiest_vendor_first():
    ranking = watchlist.rank_entities(make_snapshots(), "vendor")
    assert ranking.iloc[0][config.COL_VENDOR] == "Vendor A"
    assert ranking.set_index(config.COL_VENDOR).loc["Vendor B", "critical"] == 0


def test_profile_same_keys_at_every_level_and_is_json_safe():
    import json

    snaps, comments = make_snapshots(), make_comments()
    profiles = {
        "vendor": profile.build_profile(snaps, comments, "vendor", "Vendor A"),
        "mrp_controller": profile.build_profile(snaps, comments, "mrp_controller", "M2"),
        "material": profile.build_profile(snaps, comments, "material", 2),
    }
    common = {"level", "entity_id", "meta", "current", "history", "root_causes",
              "persistence", "watchlist", "recent_comments"}
    for p in profiles.values():
        assert common <= set(p)
        json.dumps(p)  # must not raise (no numpy / Timestamp left)
    assert "top_materials" in profiles["vendor"] and "related_vendors" in profiles["material"]
    va = profiles["vendor"]
    assert va["current"]["status_counts"]["Actual Stock Out"] == 1
    assert va["top_materials"][0][config.COL_MATERIAL] == 1  # actual stock-out ranks first
    assert va["watchlist"]["n_high"] >= 2


def test_profile_unknown_entity_is_empty_not_an_error():
    assert profile.build_profile(make_snapshots(), make_comments(), "vendor", "Nobody")["empty"] is True


def test_profile_entity_absent_from_latest_snapshot():
    p = profile.build_profile(make_snapshots(), make_comments(), "material", 6)
    assert p["meta"]["in_latest_snapshot"] is False
    assert p["current"]["elements"] == 0 and p["current"]["critical_share_pct"] is None
