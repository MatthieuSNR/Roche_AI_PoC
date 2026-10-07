import pandas as pd

from roche_poc import config
from roche_poc.data import build_tables, cleaning


def _raw():
    return pd.DataFrame(
        {
            "Snapshot_Date": ["2026-03-02", "2026-03-09", "2026-03-09", "2026-03-16", "not a date"],
            "MATERIAL_NUMBER": [1, 1, 1, 2, 2],
            "Issue": ["S_Lack of Raw Material", "S_Lack of Raw Material", "S_Lack of Raw Material", None, None],
            "comment": [
                "abc12, 2026-03-01: Waiting for material",
                "abc12, 2026-03-01: Waiting for material",
                "abc12, 2026-03-01: Waiting for material",   # exact duplicate of previous row
                "No prefix at all here",                      # must be KEPT
                None,
            ],
            "MATERIAL_STATUS": ["Actual Stock Out"] * 3 + ["Unknown Status (Good Part)", "Good Part"],
            "Impact": ["Production (Stop&Go/Stock out on the production line)", "Production", "Production",
                       "None (no impact)", None],
            "VENDOR_NAME": ["V"] * 5,
            "MRP_CONTROLLER": ["M"] * 5,
        }
    )


def test_prefix_removed_but_comment_without_prefix_is_kept():
    out, n = cleaning.strip_comment_prefix(pd.Series(["ab, 2026-01-02: Hello  world", "Plain text", None, "  "]))
    assert out.iloc[0] == "Hello world" and out.iloc[1] == "Plain text"
    assert pd.isna(out.iloc[2]) and pd.isna(out.iloc[3])
    assert n == 1


def test_clean_snapshots_report_and_normalisation():
    df, report = cleaning.clean_snapshots(_raw())
    assert report["rows_in"] == 5
    assert report["rows_invalid_snapshot_date"] == 1
    assert report["rows_exact_duplicates_removed"] == 1   # row 3 duplicates row 2 only after impact normalisation
    assert report["rows_out"] == len(df) == 3
    assert set(df[config.COL_IMPACT].dropna()) <= set(config.IMPACT_ORDER)
    assert "Unknown Status (Good Part)" not in set(df[config.COL_STATUS])
    assert "No prefix at all here" in set(df[config.COL_COMMENT].dropna())


def test_comments_table_keeps_lifetime_of_each_unique_comment():
    snaps, _ = cleaning.clean_snapshots(_raw())
    comments = build_tables.build_comments_table(snaps)
    waiting = comments[comments[config.COL_COMMENT] == "Waiting for material"].iloc[0]
    assert waiting["first_seen"] == pd.Timestamp("2026-03-02")
    assert waiting["last_seen"] == pd.Timestamp("2026-03-09")
    assert waiting["n_snapshots"] == 2
    assert len(comments) == 2


def test_load_raw_snapshots_concatenates_files_and_keeps_provenance():
    import tempfile
    from pathlib import Path

    from roche_poc.data.loading import load_raw_snapshots

    with tempfile.TemporaryDirectory() as tmp:
        pd.DataFrame({"a": [1, 2]}).to_csv(Path(tmp) / "s1.csv", index=False)
        pd.DataFrame({"a": [3]}).to_csv(Path(tmp) / "s2.csv", index=False)
        out = load_raw_snapshots(tmp)
        assert len(out) == 3 and out["source_file"].tolist() == ["s1.csv", "s1.csv", "s2.csv"]
        try:
            load_raw_snapshots(Path(tmp) / "missing")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("expected FileNotFoundError")
