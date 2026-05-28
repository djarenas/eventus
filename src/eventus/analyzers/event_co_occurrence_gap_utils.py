"""
event_co_occurrence_gap_utils.py
Per-entity nearest-neighbor gap computation for
EventCoOccurrenceAnalyzer.compute_gaps().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.analyzers.event_co_occurrence_primitives import (
    build_co_occurrence_streams,
    nearest_forward_gaps,
    gap_stats,
)


def compute_entity_gaps(
    dates_a: list,
    dates_b: list,
) -> dict:
    """
    Compute all gap statistics for one entity.

    Parameters
    ----------
    dates_a : Sorted list of A event timestamps within obs window.
    dates_b : Sorted list of B event timestamps within obs window.

    Returns
    -------
    dict with all gap columns.
    """
    # A → nearest B after each A
    a_to_b_gaps  = nearest_forward_gaps(dates_a, dates_b)
    a_to_b_stats = gap_stats(a_to_b_gaps)

    # B → nearest A after each B
    b_to_a_gaps  = nearest_forward_gaps(dates_b, dates_a)
    b_to_a_stats = gap_stats(b_to_a_gaps)

    return {
        "n_a_with_following_b": len(a_to_b_gaps),
        "mean_days_a_to_b":     a_to_b_stats["mean"],
        "median_days_a_to_b":   a_to_b_stats["median"],
        "std_days_a_to_b":      a_to_b_stats["std"],
        "n_b_with_following_a": len(b_to_a_gaps),
        "mean_days_b_to_a":     b_to_a_stats["mean"],
        "median_days_b_to_a":   b_to_a_stats["median"],
        "std_days_b_to_a":      b_to_a_stats["std"],
    }


def compute_gap_stats(
    data:       pd.DataFrame,
    entity_col: str,
    evt_col_a:  str,
    evt_col_b:  str,
) -> pd.DataFrame:
    """
    Compute gap statistics for all entities.

    Parameters
    ----------
    data       : CohortTimeline.data
    entity_col : Entity identifier column name.
    evt_col_a  : evt_{identity_a} column name.
    evt_col_b  : evt_{identity_b} column name.

    Returns
    -------
    pd.DataFrame
        One row per entity with all gap columns.
    """
    rows = []
    obs_start_col = "obs_start"
    obs_end_col   = "obs_end"

    for _, row in data.iterrows():
        obs_start = pd.Timestamp(row[obs_start_col]).normalize()
        obs_end   = pd.Timestamp(row[obs_end_col]).normalize()

        dates_a, dates_b = build_co_occurrence_streams(
            row, evt_col_a, evt_col_b, obs_start, obs_end
        )

        stats = compute_entity_gaps(dates_a, dates_b)
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = obs_start
        stats[obs_end_col]   = obs_end
        rows.append(stats)

    return pd.DataFrame(rows)
