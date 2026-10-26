"""
Insights Lab: the new pages of the dashboard, reached from the second row of the top menu (?page=...).
They are being validated: the existing page (app.py) is left unchanged until a new page replaces a section.
The sidebar filters of app.py apply here too. The analyses themselves are in scripts/insights.py.

  grouped-comments   Most frequent comments, near-identical wordings grouped (US24)
  trends-all         Root cause trends on all snapshot rows + what changed between two weeks (US26)
  cause-impact       Root cause x impact: is a root cause followed by more severe impacts?
  weak-signals       Do the first comments announce a Production / Market impact to come?
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import insights as ins
import ui
from tracking import TRACKING_PATH

PAGES = [
    ("grouped-comments", "Frequent Comments, Grouped"),
    ("trends-all", "Root Cause Trends (all snapshots)"),
    ("cause-impact", "Root Cause × Impact"),
    ("weak-signals", "Weak Signals"),
]
LAB_LABEL = "Insights Lab · new pages to validate"


@st.cache_data
def load_tracking():
    if not os.path.exists(TRACKING_PATH):
        return None
    t = pd.read_csv(TRACKING_PATH)
    t["MATERIAL_LABEL"] = t["MATERIAL_DESC"].fillna("No description") + " — " + t["MATERIAL_NUMBER"].astype("int64").astype(str)
    t["VENDOR_LABEL"] = (t["VENDOR_NAME"].fillna("Unknown vendor") + " — "
                         + t["VENDOR_ACCOUNT_NUMBER"].astype("Int64").astype(str).replace("<NA>", "no vendor"))
    t["MRP_CONTROLLER"] = t["MRP_CONTROLLER"].fillna("Unknown")
    t["PURCHASING_GROUP"] = t["PURCHASING_GROUP"].fillna("Unknown")
    return t


def filter_tracking(tracking, selections):
    """Same sidebar filters as the comments (the impact filter is left out: it is analysed here)."""
    for column, selected in selections.items():
        if selected and column in tracking.columns:
            tracking = tracking[tracking[column].isin(selected)]
    return tracking


def _missing_tracking():
    st.warning("The tracking table is missing. Build it from the snapshots: `python scripts/tracking.py` (about 20 s).")


@st.cache_resource(show_spinner="Loading the language model (first time only)...")
def _embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(ins.EMBEDDING_MODEL)


@st.cache_data(show_spinner="Grouping similar comments...")
def _groups(entries, threshold, method):
    embeddings = (lambda texts: _embedding_model().encode(list(texts), normalize_embeddings=True, batch_size=64)) \
        if method == "meaning" else None
    return ins.group_comments(entries, threshold, method, embeddings)


# ------------------------------------------------------------------ page 1
def page_grouped_comments(filtered_df, selection_name):
    ui.section("grouped-comments", "Most Frequent Comments, Grouped — " + selection_name)
    st.caption("Same table as 'Most Frequent Comments', but near-identical comments are counted as one issue "
               "(request of Johannes Höttler, 23.10). Every merge has a reason, shown under the table.")
    c1, c2, c3, c4 = st.columns([0.8, 1.3, 1.3, 1.4])
    top_n = int(c1.selectbox("Select a view:", ["Top 10", "Top 20", "Top 50"], key="lab_top").split()[1])
    method_label = c3.selectbox("Similarity of:", ["Wording (characters)", "Meaning (language model)"], key="lab_method",
                                help="Wording: same words, typos, plural forms. Meaning: a small language model "
                                     "(all-MiniLM-L6-v2, run on this machine, no data leaves it) also groups "
                                     "paraphrases such as 'No stockout detected' / 'No stockout apparent'.")
    method = "meaning" if method_label.startswith("Meaning") else "chars"
    which = c2.selectbox("Journal entries:", ["All entries", "Problem (first written entry)",
                                              "Latest status (most recent entry)"], key="lab_entries",
                         help="A comment cell is a journal written newest first: its last entry describes the "
                              "problem, its first entry the latest status.")
    threshold = c4.slider("Similarity needed to merge:", 0.40, 0.95, ins.METHODS[method], 0.05, key=f"lab_threshold_{method}",
                          help="Cosine similarity of the character sequences. Higher = stricter. Wordings with "
                               "different root causes are never merged, except when only case or punctuation differ.")
    mode = {"All entries": "all", "Problem (first written entry)": "problem",
            "Latest status (most recent entry)": "latest"}[which]
    entries = ins.comment_entries(filtered_df, mode)[["Entry", "Root_Cause", "MATERIAL_NUMBER", "VENDOR_NAME", "Days_Active"]]
    if entries.empty:
        st.info("No comments match the current filters.")
        return
    groups, variants = _groups(entries.reset_index(drop=True), threshold, method)

    m1, m2, m3 = st.columns(3)
    m1.metric("Entries", f"{len(entries):,}")
    m2.metric("Distinct wordings", f"{entries['Entry'].nunique():,}")
    m3.metric("Issues after grouping", f"{len(groups):,}",
              delta=f"{len(groups) - entries['Entry'].nunique():,}", delta_color="off")

    table = groups.head(top_n).copy()
    table.insert(3, "% of entries", (table["Occurrences"] / len(entries) * 100).round(1))
    st.dataframe(
        table.drop(columns=["Group", "Spellings"]).rename(columns={
            "Comment": "Comment (EN, most frequent wording)", "Variants": "Wordings grouped",
            "Days_visible": "Days visible (total)", "Main_root_cause": "Main root cause",
            "Root_causes": "Root causes (entries)"}),
        use_container_width=True, hide_index=True,
        column_config={"Comment (EN, most frequent wording)": st.column_config.TextColumn(width="large"),
                       "Root causes (entries)": st.column_config.TextColumn(width="large")})
    st.caption("Occurrences = entries of the group. Wordings grouped = different texts after normalisation. "
               "Main root cause = most frequent root cause entered with these comments (empty ones left aside).")

    ui.panel_header("Why were these wordings grouped?")
    choice = st.selectbox("Group:", table["Comment"].tolist(), key="lab_group")
    group_id = table.loc[table["Comment"] == choice, "Group"].iloc[0]
    st.dataframe(variants[variants["Group"] == group_id][["Wording", "Occurrences", "Main_root_cause", "Reason"]]
                 .rename(columns={"Main_root_cause": "Main root cause"}),
                 use_container_width=True, hide_index=True,
                 column_config={"Wording": st.column_config.TextColumn(width="large"),
                                "Reason": st.column_config.TextColumn(width="large")})
    with st.expander("How the grouping works"):
        st.markdown(
            "1. **Same text after normalisation**: case, punctuation and the spellings of *stock-out* and *pull-in* "
            "are ignored (`PX13` = `px13`), whatever the root cause.\n"
            "2. **One wording contained in the other** (at most 3 more words) **and the same main root cause**: "
            "`px13` and `px13 - No stockout detected`.\n"
            "3. **Similar wording or meaning** (above the threshold) **and the same main root cause**, or no root "
            "cause entered: `Request for Pull-in` and `Request to pull in the LT`.\n\n"
            "A wording joins the group of the most frequent similar wording (no chains). Two ways to measure the "
            "similarity: **wording** (character sequences: same words, typos) or **meaning** (a small English "
            "language model, *all-MiniLM-L6-v2*, run on this machine: it also groups paraphrases such as *No stockout "
            "detected* / *No stockout apparent*, 0.89). Neither knows the supply-chain jargon: *expedite* and "
            "*pull-in* stay apart (0.20 with the language model). The groups are made on the English translation.")


# ------------------------------------------------------------------ page 2
def page_trends_all(tracking, selection_name):
    ui.section("trends-all", "Root Cause Trends (all snapshots) — " + selection_name)
    if tracking is None:
        return _missing_tracking()
    with_cause = tracking.dropna(subset=["Root_Cause"])
    items_rc = with_cause.groupby(ins.ITEM).ngroups
    items_rc_no_comment = (with_cause.groupby(ins.ITEM)["Comment"].count() == 0).sum()
    st.caption(f"Counted on every snapshot row, commented or not: {items_rc:,} items (material, vendor) with a root "
               f"cause, of which {items_rc_no_comment:,} never had a comment (they are missing from the existing trend). "
               "One item counts once per week, however many order lines and days it has.")
    c1, c2 = st.columns([1, 3])
    by = c1.radio("Group by:", ["Root cause", "Stakeholder"], key="lab_trend_by",
                  help="Stakeholder = prefix of the root cause (S = Supplier, PL = Planning, P = Procurement, "
                       "B = Buying...; legend of Johannes Höttler).")
    weekly = ins.weekly_items(tracking, "Root_Cause" if by == "Root cause" else "Stakeholder")
    if weekly.empty:
        st.info("No root cause for the current filters.")
    else:
        ranking = weekly.sum().sort_values(ascending=False).index.tolist()
        shown = c2.multiselect("Lines to display (default: the 6 largest):", ranking, default=ranking[:6], key=f"lab_lines_{by}")
        if shown:
            fig, ax = plt.subplots(figsize=(12, 5.5))
            colors = plt.cm.tab20.colors if len(shown) > 8 else None
            for i, name in enumerate(shown):
                ax.plot(weekly.index, weekly[name], marker="o", markersize=3, label=name,
                        color=colors[i % 20] if colors else None)
            ax.set_title(f"Items per {by.lower()} and week — {selection_name}")
            ax.set_ylabel("Items with this root cause during the week")
            ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            first, last = weekly.index[0], weekly.index[-1]
            change = pd.DataFrame({f"Week of {first:%d.%m}": weekly.loc[first, shown],
                                   f"Week of {last:%d.%m}": weekly.loc[last, shown],
                                   "Peak": weekly[shown].max(), "Peak week": weekly[shown].idxmax().dt.strftime("%d.%m")})
            change["Change"] = change.iloc[:, 1] - change.iloc[:, 0]
            st.dataframe(change.reset_index().rename(columns={"index": by, "Root_Cause": by, "Stakeholder": by}),
                         use_container_width=True, hide_index=True)

    ui.panel_header("What changed between two weeks?")
    st.caption("Why are there more (or fewer) stock-outs this week? Items in the status at the end of each week, "
               "and the root causes of the items that entered or left it (US26, Johannes Höttler).")
    ends = ins.week_end_days(tracking)
    weeks = sorted(ends)
    if len(weeks) < 2:
        st.info("Not enough weeks for the current filters.")
        return
    c1, c2, c3 = st.columns([1.6, 1, 1])
    statuses = c1.multiselect("Status:", ["Actual Stock Out", "Potential Stock Out"], default=["Actual Stock Out"],
                              key="lab_status")
    label = lambda w: f"Week of {w:%d.%m.%Y} (snapshot {ends[w]:%d.%m})"
    week_a = c2.selectbox("From:", weeks, index=len(weeks) - 2, format_func=label, key="lab_week_a")
    week_b = c3.selectbox("To:", weeks, index=len(weeks) - 1, format_func=label, key="lab_week_b")
    if not statuses:
        return
    summary, entered, n_a, n_b = ins.status_change(tracking, ends[week_a], ends[week_b], tuple(statuses))
    st.metric(f"Items in {' / '.join(statuses)}", f"{n_a} → {n_b}", delta=f"{n_b - n_a:+d}", delta_color="inverse")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    if len(entered):
        st.markdown("**Items that entered the status, with their root cause and comment**")
        comments_en = st.session_state.get("_comments_en", {})
        shown = entered.assign(Comment_EN=entered["Comment"].map(comments_en).fillna(entered["Comment"]))
        st.dataframe(shown[["Root_Cause", "Comment_EN", "VENDOR_NAME", "MRP_CONTROLLER", "MATERIAL_LABEL"]]
                     .rename(columns={"Root_Cause": "Root cause", "Comment_EN": "Comment (EN)", "VENDOR_NAME": "Vendor",
                                      "MRP_CONTROLLER": "MRP Controller", "MATERIAL_LABEL": "Material"}),
                     use_container_width=True, hide_index=True,
                     column_config={"Comment (EN)": st.column_config.TextColumn(width="large")})


# ------------------------------------------------------------------ page 3
def page_cause_impact(tracking, selection_name):
    ui.section("cause-impact", "Root Cause × Impact — " + selection_name)
    if tracking is None:
        return _missing_tracking()
    st.caption("Is a root cause followed by more severe impacts than the others? Unit = item (material, vendor) "
               "on all snapshots: its root cause(s) and the most severe impact entered for it. The impact is entered "
               "by planning (Market > Production > Logistics > None). 'Not communicated' = nothing entered: the impact "
               "is unknown, which does not mean that there is none. The tests only use the items whose impact was "
               "communicated.")
    try:
        table, per_cause, test = ins.root_cause_impact(tracking)
    except ValueError:
        st.info("Not enough items with a communicated impact for the current filters.")
        return
    significant = test["p"] < 0.05
    st.markdown(
        f"**Chi-square test of independence** on the {test['n_items']} items with a communicated impact, for the {test['n_causes']} root "
        f"causes with at least 5 of them: χ² = {test['chi2']}, {test['dof']} degrees of freedom, "
        f"p = {test['p']:.2g} → " + ("root cause and impact are **not independent** (p < 0.05). " if significant else
                                     "no significant link between root cause and impact (p ≥ 0.05). ") +
        f"Cramér's V = **{test['cramers_v']}** "
        f"({'weak' if test['cramers_v'] < 0.2 else 'moderate' if test['cramers_v'] < 0.4 else 'strong'} association). "
        f"Overall, {test['severe_base_pct']}% of the items with a communicated impact had a Production or Market impact.")

    min_items = st.slider("Root causes with at least ... items with a communicated impact:", 1, 30, 5, key="lab_min_items")
    shown = per_cause[per_cause["Impact communicated"] >= min_items]
    order = shown["Root cause"].tolist()
    if order:
        assessed = table.loc[order].drop(columns=ins.NOT_COMMUNICATED)
        share = assessed.div(assessed.sum(axis=1), axis=0) * 100
        fig, ax = plt.subplots(figsize=(10, 0.42 * len(order) + 1.4))
        im = ax.imshow(share.to_numpy(), cmap="Reds", aspect="auto", vmin=0, vmax=100)
        ax.set_xticks(range(share.shape[1]), share.columns)
        ax.set_yticks(range(len(order)), [o if len(o) <= 40 else o[:39] + "…" for o in order], fontsize=8)
        for i in range(share.shape[0]):
            for j in range(share.shape[1]):
                n = int(assessed.iat[i, j])
                if n:
                    ax.text(j, i, f"{share.iat[i, j]:.0f}%\n({n})", ha="center", va="center", fontsize=7,
                            color="white" if share.iat[i, j] > 60 else "black")
        ax.set_title("Impact communicated per root cause (% of the items with an impact entered, count in brackets)")
        ax.spines[:].set_visible(False)
        fig.colorbar(im, ax=ax, fraction=0.025, label="% of the items with an impact entered")
        plt.tight_layout()
        st.pyplot(fig)
    st.dataframe(shown, use_container_width=True, hide_index=True,
                 column_config={"p-value": st.column_config.NumberColumn(format="%.4f")})
    st.caption("Lift = % severe of this root cause ÷ % severe of all root causes (above 1 = more severe than average). "
               "p-value = Fisher's exact test, this root cause vs all others; below 0.05 the difference is unlikely "
               "to be chance. An item with two root causes counts for both. Small counts: read with care.")


# ------------------------------------------------------------------ page 4
@st.cache_data(show_spinner="Looking for weak signals...")
def _weak_signals(tracking, comments_en):
    items = ins.weak_signal_items(tracking, comments_en)
    terms = ins.signal_terms(items)
    scores, risk, weights = ins.signal_model(items)
    items["Risk"] = risk
    return items, terms, scores, weights


def page_weak_signals(tracking, tracking_filtered, comments_en, selection_name):
    ui.section("weak-signals", "Weak Signals — " + selection_name)
    if tracking is None:
        return _missing_tracking()
    st.caption("Do the first comments on an item announce a Production or Market impact communicated LATER? Unit = item "
               "(material, vendor) with a comment; items already severe when first commented are left out. The "
               "analysis uses all items (it needs volume); the sidebar filters apply to the watch list at the bottom.")
    items, terms, scores, weights = _weak_signals(tracking, comments_en)
    severe = items[items["Severe_later"]]
    m1, m2, m3 = st.columns(3)
    m1.metric("Items with a comment", f"{len(items):,}")
    m2.metric("Severe impact communicated later", f"{len(severe):,}", delta=f"{len(severe) / len(items) * 100:.1f}%",
              delta_color="off")
    m3.metric("Median warning time", f"{severe['Days_before_impact'].median():.0f} days",
              help="Days between the first comment and the first Production / Market impact.")

    ui.panel_header("Words of the first comment followed by a severe impact")
    st.dataframe(terms.head(25), use_container_width=True, hide_index=True,
                 column_config={"p-value": st.column_config.NumberColumn(format="%.4f")})
    st.caption(f"Words or word pairs of at least 5 first comments. Lift = % severe later with this word ÷ "
               f"{len(severe) / len(items) * 100:.1f}% for all items. p-value = one-sided Fisher's exact test. "
               "The other items had no Production / Market impact communicated, which does not prove that there was none.")

    ui.panel_header("Can the first comment predict the impact?")
    if scores.empty:
        st.info("Not enough items to train a model.")
    else:
        st.dataframe(scores, use_container_width=True, hide_index=True)
        best = scores.iloc[scores["MCC"].idxmax()]
        st.caption(f"Logistic regression with balanced classes, 5-fold cross-validation on {scores.attrs['n_items']} "
                   f"items ({scores.attrs['n_severe']} severe later). MCC (Matthews correlation coefficient): 0 = no "
                   f"better than chance, 1 = perfect; it stays honest when severe items are rare. ROC AUC: 0.5 = chance. "
                   f"Best: {best['Model']} (MCC {best['MCC']}, AUC {best['ROC AUC']}). Method after Usuga-Cadavid et "
                   "al. (classic text model, MCC, word contributions).")
        with st.expander("Words and root causes that weigh most in the model"):
            st.dataframe(pd.concat([weights.head(15).assign(Direction="raises the risk"),
                                    weights.tail(10).iloc[::-1].assign(Direction="lowers the risk")]),
                         use_container_width=True, hide_index=True)

    ui.panel_header("Watch list: open items whose comments look like those that led to an impact")
    last_day = pd.to_datetime(tracking["Snapshot_Date"]).max()
    in_scope = set(map(tuple, tracking_filtered[ins.ITEM].drop_duplicates().to_numpy()))
    watch = items[(items["Last_seen"] == last_day) & ~items["Severe_later"]].copy()
    watch = watch[[(m, v) in in_scope for m, v in zip(watch["MATERIAL_NUMBER"], watch["VENDOR_ACCOUNT_NUMBER"])]]
    watch["Days since first comment"] = (last_day - watch["First_comment"]).dt.days
    watch = watch.sort_values("Risk", ascending=False).head(20)
    watch["Risk"] = (watch["Risk"] * 100).round(0).astype("Int64").astype(str) + "%"
    st.dataframe(watch[["Risk", "Text", "Root_Cause", "Days since first comment", "VENDOR_NAME", "MRP_CONTROLLER",
                        "MATERIAL_DESC"]]
                 .rename(columns={"Text": "First comment (EN)", "Root_Cause": "Root cause", "VENDOR_NAME": "Vendor",
                                  "MRP_CONTROLLER": "MRP Controller", "MATERIAL_DESC": "Material"}),
                 use_container_width=True, hide_index=True,
                 column_config={"First comment (EN)": st.column_config.TextColumn(width="large")})
    st.caption(f"Items still visible on {last_day:%d.%m.%Y} with no Production / Market impact communicated, ranked by the "
               "risk the model gives them (out-of-fold estimate). A ranking to look at first, not a forecast.")


def render(page, df, filtered_df, selections, selection_name):
    """Draw the Insights Lab page `page` (an id of PAGES)."""
    tracking = load_tracking()
    st.session_state["_comments_en"] = dict(zip(df["Comment"], df["Comment_EN"]))
    tracking_filtered = filter_tracking(tracking, selections) if tracking is not None else None
    if page == "grouped-comments":
        page_grouped_comments(filtered_df, selection_name)
    elif page == "trends-all":
        page_trends_all(tracking_filtered, selection_name)
    elif page == "cause-impact":
        page_cause_impact(tracking_filtered, selection_name)
    elif page == "weak-signals":
        page_weak_signals(tracking, tracking_filtered, st.session_state["_comments_en"], selection_name)
