"""Robust trend indicators.

The first prototype compared the first and the last snapshot, which rests on two
points only and is dominated by noise (and, there, by the de-duplication artefact).
Here the trend is the least-squares slope over ALL points, and no trend is claimed
when there are too few points.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from roche_poc import config


def slope(values: Sequence[float]) -> float:
    """Least-squares slope per snapshot step (NaN with fewer than 2 valid points)."""
    y = np.asarray(pd.Series(values, dtype=float).dropna(), dtype=float)
    if len(y) < 2:
        return float("nan")
    return float(np.polyfit(np.arange(len(y)), y, 1)[0])


def trend_label(values: Sequence[float]) -> str:
    """'rising', 'falling', 'stable' or 'insufficient data'."""
    y = pd.Series(values, dtype=float).dropna()
    if len(y) < config.MIN_POINTS_FOR_TREND:
        return "insufficient data"
    s = slope(y)
    mean = float(y.mean())
    if mean == 0:
        return "stable" if s == 0 else ("rising" if s > 0 else "falling")
    rel = s / abs(mean)
    if rel > config.TREND_REL_SLOPE:
        return "rising"
    if rel < -config.TREND_REL_SLOPE:
        return "falling"
    return "stable"


def rolling_mean(series: pd.Series, window: int = 4) -> pd.Series:
    """Centered-free rolling mean (uses available points at the start)."""
    return series.rolling(window=window, min_periods=1).mean()


def trend_summary(series: pd.Series) -> dict:
    """Compact, JSON-friendly description of a time series."""
    clean = series.dropna()
    return {
        "label": trend_label(clean),
        "n_points": int(len(clean)),
        "slope_per_snapshot": None if len(clean) < 2 else round(slope(clean), 4),
        "first": None if clean.empty else round(float(clean.iloc[0]), 4),
        "last": None if clean.empty else round(float(clean.iloc[-1]), 4),
        "mean": None if clean.empty else round(float(clean.mean()), 4),
    }
