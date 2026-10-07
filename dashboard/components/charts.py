"""Matplotlib charts (pure functions: no Streamlit import, so they are testable)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # safe in headless / test environments
import matplotlib.pyplot as plt
import pandas as pd

from roche_poc import config


def status_timeline_chart(records: list[dict]):
    """Stacked bars: number of MRP elements per status at each snapshot."""
    df = pd.DataFrame(records)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    if df.empty:
        ax.text(0.5, 0.5, "No history", ha="center", va="center")
        ax.axis("off")
        return fig
    df[config.COL_SNAPSHOT] = pd.to_datetime(df[config.COL_SNAPSHOT])
    df = df.set_index(config.COL_SNAPSHOT)
    bottom = pd.Series(0, index=df.index, dtype=float)
    for status in config.STATUS_ORDER:
        if status in df.columns:
            ax.bar(df.index, df[status], bottom=bottom, width=5, label=status,
                   color=config.STATUS_COLORS[status])
            bottom += df[status]
    ax.set_ylabel("MRP elements")
    ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.2), frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def critical_share_chart(records: list[dict], trend_label: str = ""):
    """Line: share of critical elements per snapshot, with a 4-snapshot rolling mean."""
    df = pd.DataFrame(records)
    fig, ax = plt.subplots(figsize=(8, 2.6))
    if df.empty:
        ax.axis("off")
        return fig
    df[config.COL_SNAPSHOT] = pd.to_datetime(df["_snap"] if "_snap" in df else df[config.COL_SNAPSHOT])
    series = df.set_index(config.COL_SNAPSHOT)["critical_share"] * 100
    ax.plot(series.index, series.values, marker="o", color=config.STATUS_COLORS[config.STATUS_ACTUAL], label="Critical share")
    ax.plot(series.index, series.rolling(4, min_periods=1).mean(), color="#555", linestyle="--", label="4-snapshot mean")
    ax.set_ylabel("% critical")
    ax.set_ylim(bottom=0)
    ax.set_title(f"Trend: {trend_label}" if trend_label else "", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def root_cause_chart(records: list[dict]):
    """Horizontal bars: root causes by element-snapshots (exposure)."""
    df = pd.DataFrame(records)
    fig, ax = plt.subplots(figsize=(6, max(2, 0.45 * max(len(df), 1))))
    if df.empty:
        ax.text(0.5, 0.5, "No root cause recorded", ha="center", va="center")
        ax.axis("off")
        return fig
    df = df.iloc[::-1]
    bars = ax.barh(df[config.COL_ROOT_CAUSE], df["n_rows"], color="#4c78a8")
    for bar, pct in zip(bars, df["pct_of_known"]):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f" {pct:.0f}%", va="center", fontsize=8)
    ax.set_xlabel("Element-snapshots")
    ax.margins(x=0.15)
    fig.tight_layout()
    return fig
