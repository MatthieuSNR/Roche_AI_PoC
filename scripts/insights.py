"""
Analyses of the new dashboard pages (Insights Lab, scripts/insights_pages.py). pandas / scikit-learn / scipy
only, no Streamlit here, so that every function can be tested and run in a notebook.

1. group_comments       near-identical comments counted as one issue (US24, Johannes 23.10)
2. weekly_items         root cause trend on ALL snapshot rows (data/item_tracking.csv), by root cause or stakeholder
   status_change        why the number of stock-outs changed between two weeks (US26)
3. root_cause_impact    root cause x impact: contingency table, chi-square, Cramér's V, lift per root cause
4. weak_signals         do the first comments of an item announce a Production / Market impact to come?

Grouping (1) is explainable on purpose: every merge has a reason shown in the dashboard.
  a. same text after normalisation (case, punctuation, "stock-out" / "stock out" / "stockout"), whatever the root cause;
  b. one text contained in the other (at most MAX_EXTRA_WORDS more words) AND the same main root cause:
     "px13" and "px13 - No stockout detected";
  c. similar wording (cosine of character 3-5-grams >= threshold) AND the same main root cause (or none entered):
     "Request for pull-in" and "Request to pull in the LT".
  A variant joins the group of the most frequent similar variant (no chaining A~B~C), so a group stays readable.
Classic text features are used rather than a deep model: on short, code-like texts (px13, LT, svc) they are
as good as transformers (Usuga-Cadavid et al., predictive maintenance logs) and every decision can be explained.
"""

import re

import numpy as np
import pandas as pd

from entries import split_cell

NO_ROOT_CAUSE = "(no root cause)"
ITEM = ["MATERIAL_NUMBER", "VENDOR_ACCOUNT_NUMBER"]
SEVERE_IMPACTS = ["Market", "Production"]
NOT_COMMUNICATED = "Not communicated"   # no impact entered: unknown, NOT "no impact"
IMPACT_COLUMNS = ["Market", "Production", "Logistics", "None (no impact)", NOT_COMMUNICATED]
MAX_EXTRA_WORDS = 3
# Stakeholder responsible for a root cause = prefix of its name (legend from Johannes Höttler, 21.10)
STAKEHOLDERS = {"S": "Supplier", "B": "Buying", "P": "Procurement", "I": "Import/Export", "M": "Material Management",
                "PE": "PE", "PL": "Planning", "PR": "Production", "C": "Complaint Center", "TSM": "TSM", "E": "External"}


def stakeholder(root_cause):
    """'PL_Shortterm demand' -> 'Planning'; a root cause without prefix ('QM Lot') -> 'Other'."""
    if pd.isna(root_cause):
        return NO_ROOT_CAUSE
    prefix = str(root_cause).split("_", 1)[0]
    return STAKEHOLDERS.get(prefix, "Other") if "_" in str(root_cause) else "Other"


# ------------------------------------------------------------------ 1. grouping of similar comments
def normalise(text):
    text = str(text).lower()
    text = re.sub(r"stock[\s-]?outs?", "stockout", text)
    text = re.sub(r"pull[\s-]?ins?", "pullin", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def comment_entries(df, which="all", text_column="Comment_EN"):
    """One row per journal entry. The journal is written newest first (checked on the data: 171 cells
    newest first, 8 oldest first), so the LAST entry of a cell describes the problem and the FIRST one
    the latest status (Johannes, US25). which = 'all' | 'problem' | 'latest'."""
    rows = df.dropna(subset=[text_column]).copy()
    rows["_entries"] = rows[text_column].map(lambda c: [e for e in split_cell(c) if e])
    if which == "problem":
        rows["_entries"] = rows["_entries"].map(lambda e: e[-1:])
    elif which == "latest":
        rows["_entries"] = rows["_entries"].map(lambda e: e[:1])
    rows = rows.explode("_entries").dropna(subset=["_entries"])
    return rows.rename(columns={"_entries": "Entry"})


DATE = re.compile(r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b")


def neutral_label(wordings):
    """Group label without the dates and numbers that vary between its wordings: the group
    "25 estimated time of arrival 9/7-9/9", "40 estimated time of arrival 7/28"... is labelled
    "[n] estimated time of arrival [date]". Unchanged when the numbers are the same in all wordings."""
    label = wordings[0]
    without = {" ".join(re.sub(r"\d+", " ", normalise(w)).split()) for w in wordings}
    digits = {tuple(re.findall(r"\d+", w)) for w in wordings}
    if len(wordings) < 2 or len(digits) < 2 or len(without) == len(wordings):
        return label
    label = DATE.sub("[date]", label)
    label = re.sub(r"\[date\]\s*-\s*\[date\]", "[date]", label)
    return re.sub(r"\b\d+(?:[.,]\d+)?\b", "[n]", label)


def _main_root_cause(series):
    known = series.dropna()
    return known.mode().iloc[0] if len(known) else NO_ROOT_CAUSE


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # 90 MB, runs on this Mac, no data leaves it
METHODS = {"chars": 0.55, "meaning": 0.80}   # default similarity threshold of each method


def embed(texts, model_name=EMBEDDING_MODEL):
    """Sentence embeddings (normalised), computed locally. The model is downloaded once (Hugging Face cache)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name).encode(list(texts), normalize_embeddings=True, batch_size=64)


def group_comments(entries, threshold=None, method="chars", embeddings=None):
    """Groups of near-identical entries. entries: one row per entry with Entry, Root_Cause, MATERIAL_NUMBER,
    VENDOR_NAME, Days_Active. method = 'chars' (similarity of the character 3-5-grams: same words, typos) or
    'meaning' (similarity of sentence embeddings: paraphrases such as "No stockout detected" / "No stockout
    apparent"); embeddings = function texts -> vectors for 'meaning' (default: embed). Returns (groups, variants):
      groups   one row per group: Group, Comment (most frequent wording), Variants, Occurrences, Materials,
               Vendors, Days_visible, Main_root_cause, Root_causes ("A 29 · B 22")
      variants one row per normalised wording with its Group and the reason it joined the group."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    entries = entries.assign(_norm=entries["Entry"].map(normalise))
    entries = entries[entries["_norm"] != ""]
    variants = (entries.groupby("_norm")
                .agg(Wording=("Entry", lambda s: s.value_counts().index[0]), Occurrences=("Entry", "size"),
                     Main_root_cause=("Root_Cause", _main_root_cause),
                     Spellings=("Entry", "nunique"))
                .sort_values(["Occurrences", "Wording"], ascending=[False, True]).reset_index())
    if variants.empty:
        return pd.DataFrame(), variants

    threshold = METHODS[method] if threshold is None else threshold
    if method == "meaning":
        vectors = np.asarray((embeddings or embed)(variants["Wording"]))
        similarity = lambda anchors, i: vectors[anchors] @ vectors[i]
        kind = "similar meaning"
    else:
        vectors = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit_transform(variants["_norm"])
        similarity = lambda anchors, i: (vectors[anchors] @ vectors[i].T).toarray().ravel()
        kind = "similar wording"
    words = [set(n.split()) for n in variants["_norm"]]
    anchors, group_of, reason = [], [], []
    for i in range(len(variants)):
        best, best_reason, best_score = None, "", 0.0
        if anchors:
            scores = similarity(anchors, i)
            for a, score in sorted(zip(anchors, scores), key=lambda x: -x[1]):
                same_cause = variants.at[a, "Main_root_cause"] == variants.at[i, "Main_root_cause"]
                no_cause = NO_ROOT_CAUSE in (variants.at[a, "Main_root_cause"], variants.at[i, "Main_root_cause"])
                small, big = sorted((words[a], words[i]), key=len)
                contained = small <= big and len(big) - len(small) <= MAX_EXTRA_WORDS
                if same_cause and contained:
                    best, best_reason = a, "contained in the other wording, same root cause"
                elif (same_cause or no_cause) and score >= threshold and score > best_score:
                    best, best_score = a, score
                    best_reason = f"{kind} ({score:.2f}), " + ("same root cause" if same_cause else "no root cause entered")
                if best is not None and best_reason.startswith("contained"):
                    break
                if score < threshold and best is not None:
                    break
        if best is None:
            anchors.append(i)
            group_of.append(i)
            reason.append("group label (most frequent wording)")
        else:
            group_of.append(group_of[best])
            reason.append(best_reason)
    variants["Group"] = group_of
    variants["Reason"] = [r + (f" + {s} spellings (case, punctuation)" if s > 1 else "")
                          for r, s in zip(reason, variants["Spellings"])]

    entries = entries.merge(variants[["_norm", "Group"]], on="_norm")
    labels = variants.groupby("Group")["Wording"].agg(lambda w: neutral_label(list(w)))
    groups = (entries.groupby("Group")
              .agg(Occurrences=("Entry", "size"), Materials=("MATERIAL_NUMBER", "nunique"),
                   Vendors=("VENDOR_NAME", "nunique"), Days_visible=("Days_Active", "sum"),
                   Main_root_cause=("Root_Cause", _main_root_cause),
                   Root_causes=("Root_Cause", lambda s: " · ".join(f"{k} {v}" for k, v in
                                                                   s.fillna(NO_ROOT_CAUSE).value_counts().items())),
                   Variants=("_norm", "nunique"), Spellings=("Entry", "nunique"))
              .reset_index())
    groups.insert(1, "Comment", groups["Group"].map(labels))
    groups = groups.sort_values(["Occurrences", "Days_visible"], ascending=False).reset_index(drop=True)
    return groups, variants.drop(columns="_norm")


# ------------------------------------------------------------------ 2. trends on all snapshots
def weekly_items(tracking, by="Root_Cause"):
    """Number of items (material, vendor) carrying each root cause (or stakeholder) during each week,
    from every snapshot row, commented or not. Index = Monday of the week, one column per value."""
    rc = tracking.dropna(subset=["Root_Cause"]).copy()
    if rc.empty:
        return pd.DataFrame()
    rc["Week"] = pd.to_datetime(rc["Snapshot_Date"]).dt.to_period("W").dt.start_time
    rc["Stakeholder"] = rc["Root_Cause"].map(stakeholder)
    rc["Item"] = rc["MATERIAL_NUMBER"].astype(str) + "|" + rc["VENDOR_ACCOUNT_NUMBER"].astype(str)
    return rc.groupby(["Week", by])["Item"].nunique().unstack(fill_value=0)


def week_end_days(tracking):
    """{Monday of the week: last snapshot day of that week}."""
    days = pd.Series(pd.to_datetime(tracking["Snapshot_Date"].unique())).sort_values()
    return days.groupby(days.dt.to_period("W").dt.start_time).max().to_dict()


def status_change(tracking, day_a, day_b, statuses=("Actual Stock Out",)):
    """Items in the given status(es) on day_a vs day_b: which items entered / left, and their root causes.
    Returns (summary by root cause, items that entered with their root cause and comment)."""
    t = tracking.assign(Snapshot_Date=pd.to_datetime(tracking["Snapshot_Date"]))
    in_status = t[t["MATERIAL_STATUS"].isin(statuses)]
    a = in_status[in_status["Snapshot_Date"] == day_a].set_index(ITEM)
    b = in_status[in_status["Snapshot_Date"] == day_b].set_index(ITEM)
    entered = b.loc[b.index.difference(a.index)]
    left = a.loc[a.index.difference(b.index)]
    cause = lambda frame: frame["Root_Cause"].fillna(NO_ROOT_CAUSE)
    summary = pd.DataFrame({"Entered": cause(entered).value_counts(), "Left": cause(left).value_counts(),
                            f"On {day_b:%d.%m}": cause(b).value_counts()}).fillna(0).astype(int)
    summary["Net change"] = summary["Entered"] - summary["Left"]
    summary = summary.sort_values(["Net change", "Entered"], ascending=False)
    summary.index.name = "Root cause"
    return summary.reset_index(), entered.reset_index(), len(a), len(b)


# ------------------------------------------------------------------ 3. root cause x impact
def item_root_cause_impact(tracking):
    """One row per (item, root cause): the most severe impact entered for the item ('Not communicated' if none)."""
    order = {level: i for i, level in enumerate(IMPACT_COLUMNS)}
    worst = (tracking.dropna(subset=["Impact_Level"]).assign(_r=lambda d: d["Impact_Level"].map(order))
             .sort_values("_r").groupby(ITEM)["Impact_Level"].first())
    pairs = tracking.dropna(subset=["Root_Cause"]).drop_duplicates(ITEM + ["Root_Cause"])[ITEM + ["Root_Cause"]]
    pairs = pairs.join(worst, on=ITEM)
    pairs["Impact_Level"] = pairs["Impact_Level"].fillna(NOT_COMMUNICATED)
    return pairs


def root_cause_impact(tracking, min_items=5):
    """Contingency table root cause x impact (items), the chi-square test of independence on the items whose impact was communicated,
    Cramér's V, and per root cause: share of severe impacts (Production + Market) among the items whose
    impact was communicated (items without impact entered are left out: their impact is unknown),
    lift vs all root causes and Fisher's exact test (this root cause vs the others)."""
    from scipy.stats import chi2_contingency, fisher_exact

    pairs = item_root_cause_impact(tracking)
    table = pd.crosstab(pairs["Root_Cause"], pairs["Impact_Level"]).reindex(columns=IMPACT_COLUMNS, fill_value=0)
    assessed = table.drop(columns=NOT_COMMUNICATED)
    tested = assessed[assessed.sum(axis=1) >= min_items]
    tested = tested.loc[:, tested.sum() > 0]
    chi2, p, dof, _ = chi2_contingency(tested)
    n = tested.to_numpy().sum()
    cramers_v = float(np.sqrt(chi2 / (n * (min(tested.shape) - 1))))

    severe = assessed[SEVERE_IMPACTS].sum(axis=1)
    total_assessed = assessed.sum(axis=1)
    base = severe.sum() / total_assessed.sum()
    rows = []
    for cause in table.index:
        s, a = int(severe[cause]), int(total_assessed[cause])
        other_s, other_a = int(severe.sum() - s), int(total_assessed.sum() - a)
        p_cause = fisher_exact([[s, a - s], [other_s, other_a - other_s]], alternative="two-sided")[1] if a else np.nan
        rows.append({"Root cause": cause, "Stakeholder": stakeholder(cause), "Items": int(table.loc[cause].sum()),
                     "Impact communicated": a, "Severe (Prod.+Market)": s,
                     "% severe": round(s / a * 100, 1) if a else np.nan,
                     "Lift": round(s / a / base, 2) if a and base else np.nan,
                     "p-value": round(p_cause, 4) if a else np.nan})
    per_cause = pd.DataFrame(rows).sort_values(["p-value", "Items"], ascending=[True, False]).reset_index(drop=True)
    test = {"chi2": round(float(chi2), 1), "dof": int(dof), "p": float(p), "cramers_v": round(cramers_v, 2),
            "n_items": int(n), "n_causes": len(tested), "severe_base_pct": round(base * 100, 1)}
    return table, per_cause, test


# ------------------------------------------------------------------ 4. weak signals
def weak_signal_items(tracking, comments_en):
    """One row per item with a comment: its first comment (in English), the root cause at that time, and
    whether a severe impact (Production / Market) was communicated LATER (False = none communicated, which may
    also mean that the impact was never entered). Items already severe on the day of
    their first comment are left out: there is nothing to anticipate."""
    t = tracking.assign(Snapshot_Date=pd.to_datetime(tracking["Snapshot_Date"]))
    commented = t.dropna(subset=["Comment"]).sort_values("Snapshot_Date")
    first = commented.groupby(ITEM).first()[["Snapshot_Date", "Comment", "Root_Cause", "VENDOR_NAME",
                                              "MRP_CONTROLLER", "MATERIAL_DESC"]]
    first = first.rename(columns={"Snapshot_Date": "First_comment"})
    severe_day = t[t["Impact_Level"].isin(SEVERE_IMPACTS)].groupby(ITEM)["Snapshot_Date"].min().rename("First_severe")
    last_seen = t.groupby(ITEM)["Snapshot_Date"].max().rename("Last_seen")
    items = first.join(severe_day).join(last_seen).reset_index()
    items = items[~(items["First_severe"] <= items["First_comment"])]
    items["Severe_later"] = items["First_severe"].notna()
    items["Days_before_impact"] = (items["First_severe"] - items["First_comment"]).dt.days
    items["Text"] = items["Comment"].map(comments_en).fillna(items["Comment"]).str.replace("¦▸", " ", regex=False)
    items["Root_Cause"] = items["Root_Cause"].fillna(NO_ROOT_CAUSE)
    return items.reset_index(drop=True)


def signal_terms(items, min_items=5, max_p=0.1):
    """Words and word pairs of the first comments that are followed by a severe impact more often than
    average: items with the term, how many became severe, lift, one-sided Fisher exact test."""
    from scipy.stats import fisher_exact
    from sklearn.feature_extraction.text import CountVectorizer

    vec = CountVectorizer(binary=True, ngram_range=(1, 2), min_df=min_items, stop_words="english",
                          token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b")
    x = vec.fit_transform(items["Text"].str.lower())
    y = items["Severe_later"].to_numpy()
    n_pos, n = int(y.sum()), len(y)
    has = x.toarray().astype(bool)
    rows = []
    for j, term in enumerate(vec.get_feature_names_out()):
        with_term = has[:, j]
        k, m = int((y & with_term).sum()), int(with_term.sum())
        p = fisher_exact([[k, m - k], [n_pos - k, n - m - (n_pos - k)]], alternative="greater")[1]
        rows.append({"Term": term, "Items": m, "Severe later": k, "% severe later": round(k / m * 100, 1),
                     "Lift": round(k / m / (n_pos / n), 2), "p-value": round(p, 4)})
    terms = pd.DataFrame(rows)
    return terms[(terms["p-value"] <= max_p) & (terms["Lift"] > 1)].sort_values(["p-value", "Lift"], ascending=[True, False])


def signal_model(items, folds=5, seed=0):
    """Can the first comment predict a severe impact to come? Logistic regression (balanced classes) on
    TF-IDF words, on the root cause alone, and on both; 5-fold stratified cross-validation, scored with the
    Matthews correlation coefficient (robust to imbalanced classes, as in Usuga-Cadavid et al.).
    Returns (scores per model, out-of-fold risk per item for the text + root cause model, top words)."""
    from scipy.sparse import hstack
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import matthews_corrcoef, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import OneHotEncoder

    y = items["Severe_later"].to_numpy().astype(int)
    if y.sum() < folds or (len(y) - y.sum()) < folds:
        return pd.DataFrame(), pd.Series(dtype=float), pd.DataFrame()
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)

    def features(train, test, kind):
        parts_train, parts_test, names = [], [], []
        if kind in ("text", "both"):
            # min_df=5: a word must appear in 5 comments, which also keeps isolated person names out
            tf = TfidfVectorizer(ngram_range=(1, 2), min_df=5, stop_words="english", sublinear_tf=True)
            parts_train.append(tf.fit_transform(items["Text"].iloc[train]))
            parts_test.append(tf.transform(items["Text"].iloc[test]))
            names += list(tf.get_feature_names_out())
        if kind in ("cause", "both"):
            oh = OneHotEncoder(handle_unknown="ignore")
            parts_train.append(oh.fit_transform(items[["Root_Cause"]].iloc[train]))
            parts_test.append(oh.transform(items[["Root_Cause"]].iloc[test]))
            names += [f"[root cause] {c}" for c in oh.categories_[0]]
        return hstack(parts_train).tocsr(), hstack(parts_test).tocsr(), names

    scores, risk = [], pd.Series(np.nan, index=items.index)
    for kind, label in [("cause", "Root cause only"), ("text", "Comment text only"), ("both", "Comment + root cause")]:
        prob = np.zeros(len(y))
        for train, test in cv.split(items, y):
            x_train, x_test, _ = features(train, test, kind)
            model = LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0).fit(x_train, y[train])
            prob[test] = model.predict_proba(x_test)[:, 1]
        pred = (prob >= 0.5).astype(int)
        scores.append({"Model": label, "MCC": round(matthews_corrcoef(y, pred), 3),
                       "Precision": round(precision_score(y, pred, zero_division=0), 3),
                       "Recall": round(recall_score(y, pred), 3), "ROC AUC": round(roc_auc_score(y, prob), 3)})
        if kind == "both":
            risk[:] = prob
    all_rows = np.arange(len(y))
    x_all, _, names = features(all_rows, all_rows[:1], "both")
    model = LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0).fit(x_all, y)
    weights = pd.DataFrame({"Feature": names, "Weight": model.coef_[0].round(3)})
    weights = weights.sort_values("Weight", ascending=False).reset_index(drop=True)
    scores = pd.DataFrame(scores)
    scores.attrs.update(n_items=len(y), n_severe=int(y.sum()))
    return scores, risk, weights
