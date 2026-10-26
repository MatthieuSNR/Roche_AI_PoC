"""Insights Lab (insights.py, tracking.py): grouping of similar comments, tracking table, status change,
root cause x impact, weak signals. Synthetic data only, no network."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import insights as ins  # noqa: E402
import tracking as tr  # noqa: E402


def entries(rows):
    return pd.DataFrame([{"Entry": text, "Root_Cause": cause, "MATERIAL_NUMBER": i, "VENDOR_NAME": "V", "Days_Active": 1}
                         for i, (text, cause, n) in enumerate(rows) for _ in range(n)])


def test_grouping_case_containment_similarity_and_root_cause():
    groups, variants = ins.group_comments(entries([
        ("px13", "PL_Internal Errors", 5), ("PX13", "PL_Shortterm demand", 3),          # case only: merged anyway
        ("px13 - No stockout detected", "PL_Internal Errors", 4),                      # contained, same cause
        ("no stockout", "Data error dashboard", 6), ("No stockout detected", "Data error dashboard", 2),
        ("px13 Wave 2", "PE_Design/Material Changes (ECR)", 2),                        # contained, other cause
        ("Request for Pull-in", "PL_Shortterm demand", 5), ("Request to pull in the LT", "PL_Shortterm demand", 3),
    ]))
    group_of = {w.lower(): g for w, g in zip(variants["Wording"], variants["Group"])}
    assert group_of["px13"] == group_of["px13 - no stockout detected"]
    assert group_of["no stockout"] == group_of["no stockout detected"]
    assert group_of["px13 - no stockout detected"] != group_of["no stockout"]       # different root causes
    assert group_of["px13 wave 2"] != group_of["px13"]
    assert group_of["request for pull-in"] == group_of["request to pull in the lt"]
    px13 = groups[groups["Comment"].str.lower() == "px13"].iloc[0]
    assert px13["Occurrences"] == 12 and px13["Main_root_cause"] == "PL_Internal Errors"


def test_journal_problem_and_latest_entries():
    df = pd.DataFrame({"Comment_EN": ["solved ¦▸ supplier asked ¦▸ delay announced"], "Root_Cause": ["X"]})
    assert list(ins.comment_entries(df, "problem")["Entry"]) == ["delay announced"]   # written first, shown last
    assert list(ins.comment_entries(df, "latest")["Entry"]) == ["solved"]
    assert len(ins.comment_entries(df)) == 3


def test_stakeholder_prefix():
    assert ins.stakeholder("PL_Shortterm demand") == "Planning"
    assert ins.stakeholder("S_Lack of Raw Material") == "Supplier"
    assert ins.stakeholder("QM Lot") == "Other"


def merged_snapshots():
    rows = []
    for day, status, cause, impact, comment in [
        ("2026-09-01", "Actual Stock Out", None, None, "abc12, 2026-09-01: Request for pull-in"),
        ("2026-09-08", "Actual Stock Out", "PL_Shortterm demand", "Production (Stop&Go/...)", None),
    ]:
        for line in range(2):   # two order lines of the same item: one row per item and day
            rows.append({"Snapshot_Date": day, "MATERIAL_NUMBER": 1, "VENDOR_ACCOUNT_NUMBER": 10, "VENDOR_NAME": "ACME",
                         "MATERIAL_DESC": "Part", "MRP_CONTROLLER": "E1", "PURCHASING_GROUP": "G1", "PLANT": 1,
                         "MATERIAL_STATUS": status if line else "Good Part", "Root_Cause": cause,
                         "Impact": impact if line else None, "Comment": comment})
    rows.append({"Snapshot_Date": "2026-09-08", "MATERIAL_NUMBER": 2, "VENDOR_ACCOUNT_NUMBER": 20, "VENDOR_NAME": "BOLT",
                 "MATERIAL_DESC": "Screw", "MRP_CONTROLLER": "E1", "PURCHASING_GROUP": "G1", "PLANT": 1,
                 "MATERIAL_STATUS": "Actual Stock Out", "Root_Cause": "S_Lack of Raw Material", "Impact": "None",
                 "Comment": None})
    return pd.DataFrame(rows)


def test_tracking_one_row_per_item_and_day_without_logins():
    t = tr.build_tracking(merged_snapshots())
    assert len(t) == 3
    day2 = t[(t["MATERIAL_NUMBER"] == 1) & (t["Snapshot_Date"] == "2026-09-08")].iloc[0]
    assert day2["MATERIAL_STATUS"] == "Actual Stock Out" and day2["Impact_Level"] == "Production" and day2["N_Lines"] == 2
    assert t["Comment"].dropna().tolist() == ["Request for pull-in"]                   # login removed
    assert tr.impact_level("None (no impact)") == "None (no impact)" and tr.impact_level(None) is None


def test_status_change_and_weak_signal_items():
    t = tr.build_tracking(merged_snapshots())
    summary, entered, n_a, n_b = ins.status_change(t, pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-08"))
    assert (n_a, n_b) == (1, 2) and entered["Root_Cause"].tolist() == ["S_Lack of Raw Material"]
    items = ins.weak_signal_items(t, {"Request for pull-in": "Request for pull-in"})
    assert len(items) == 1 and items["Severe_later"].iloc[0] and items["Days_before_impact"].iloc[0] == 7


def test_root_cause_impact_table():
    t = pd.DataFrame({"MATERIAL_NUMBER": range(40), "VENDOR_ACCOUNT_NUMBER": 1,
                      "Root_Cause": ["A"] * 20 + ["B"] * 20,
                      "Impact_Level": ["Production"] * 16 + ["None (no impact)"] * 4 + ["Production"] * 4 + ["None (no impact)"] * 16})
    table, per_cause, test = ins.root_cause_impact(t)
    assert test["p"] < 0.05 and test["n_items"] == 40
    a = per_cause.set_index("Root cause").loc["A"]
    assert a["% severe"] == 80.0 and a["Lift"] == 1.6


def test_label_of_a_group_whose_dates_vary():
    assert ins.neutral_label(["25 estimated time of arrival 9/7-9/9", "40 estimated time of arrival 7/28"]) \
        == "[n] estimated time of arrival [date]"
    assert ins.neutral_label(["px13", "px13 Pilot"]) == "px13"                    # same numbers: unchanged


def test_grouping_by_meaning_uses_the_given_embeddings():
    vectors = {"no stockout detected": [1, 0], "no stockout apparent": [0.95, 0.31], "request for pull-in": [0, 1]}
    fake = lambda texts: [vectors[t.lower()] for t in texts]               # no model download in the tests
    groups, variants = ins.group_comments(entries([("No stockout detected", "D", 3), ("No stockout apparent", "D", 1),
                                                   ("Request for pull-in", "D", 2)]), method="meaning", embeddings=fake)
    group_of = dict(zip(variants["Wording"].str.lower(), variants["Group"]))
    assert group_of["no stockout detected"] == group_of["no stockout apparent"] != group_of["request for pull-in"]
    assert "similar meaning" in variants.set_index("Wording").loc["No stockout apparent", "Reason"]
