"""Persistence of critical states: is a problem punctual or chronic?

A material is "critical" in a snapshot when at least one of its MRP elements has a
critical status. The matrix is built over the snapshots present in the frame given
(pass the portfolio history, not a single week).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from roche_poc import config
from roche_poc.stats.kpis import is_critical

_OUT_COLUMNS = ["n_critical_snapshots", "current_streak", "episodes", "first_critical", "last_critical"]


def critical_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Boolean matrix: rows = materials, columns = snapshot dates (sorted)."""
    flagged = df.assign(_snap=pd.to_datetime(df[config.COL_SNAPSHOT]), _crit=is_critical(df))
    matrix = (
        flagged.groupby([config.COL_MATERIAL, "_snap"])["_crit"]
        .max()
        .unstack(fill_value=False)
        .astype(bool)
        .sort_index(axis=1)
    )
    return matrix


def critical_streaks(df: pd.DataFrame) -> pd.DataFrame:
    """Per material: weeks critical, current consecutive streak, number of episodes.

    * ``current_streak``: consecutive critical snapshots ending at the LAST snapshot
      (0 if the material is not critical now);
    * ``episodes``: number of separate critical periods (recurrence indicator).
    """
    matrix = critical_matrix(df)
    if matrix.empty:
        return pd.DataFrame(columns=_OUT_COLUMNS)
    flags = matrix.to_numpy()
    dates = matrix.columns.to_numpy()

    streak = np.zeros(len(flags), dtype=int)
    alive = np.ones(len(flags), dtype=bool)
    for j in range(flags.shape[1] - 1, -1, -1):
        alive &= flags[:, j]
        streak += alive

    starts = flags[:, 0].astype(int) + (flags[:, 1:] & ~flags[:, :-1]).sum(axis=1)
    any_flag = flags.any(axis=1)
    first_idx = flags.argmax(axis=1)
    last_idx = flags.shape[1] - 1 - flags[:, ::-1].argmax(axis=1)

    result = pd.DataFrame(
        {
            "n_critical_snapshots": flags.sum(axis=1),
            "current_streak": streak,
            "episodes": starts,
            "first_critical": np.where(any_flag, dates[first_idx], np.datetime64("NaT")),
            "last_critical": np.where(any_flag, dates[last_idx], np.datetime64("NaT")),
        },
        index=matrix.index,
    )
    result["first_critical"] = pd.to_datetime(result["first_critical"])
    result["last_critical"] = pd.to_datetime(result["last_critical"])
    return result
