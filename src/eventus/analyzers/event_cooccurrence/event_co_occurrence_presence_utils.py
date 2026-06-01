"""
event_co_occurrence_presence_utils.py
Per-entity presence computation for
EventCoOccurrenceAnalyzer.compute_presence().

Computes binary presence only — did each entity have at least one
A event, at least one B event, or both within the observation period?

For windowed co-occurrence computation (did B happen within N days
of A?) see event_co_occurrence_windowed_utils.py (planned).
"""
from __future__ import annotations

import pandas as pd

from eventus.analyzers.event_cooccurrence.event_co_occurrence_primitives import (
    build_co_occurrence_streams,
)


def compute_entity_presence(
    dates_a: list,
    dates_b: list,
) -> dict:
    """
    Compute binary presence statistics for one entity.

    Parameters
    ----------
    dates_a : Sorted list of A event timestamps within obs window.
    dates_b : Sorted list of B event timestamps within obs window.

    Returns
    -------
    dict with keys: n_a, n_b, has_a, has_b, has_both
    """
    n_a = len(dates_a)
    n_b = len(dates_b)

    return {
        "n_a":      n_a,
        "n_b":      n_b,
        "has_a":    n_a > 0,
        "has_b":    n_b > 0,
        "has_both": n_a > 0 and n_b > 0,
    }


def compute_presence_stats(
    data:       pd.DataFrame,
    entity_col: str,
    evt_col_a:  str,
    evt_col_b:  str,
) -> pd.DataFrame:
    """
    Compute presence statistics for all entities.

    Parameters
    ----------
    data       : CohortTimeline.data
    entity_col : Entity identifier column name.
    evt_col_a  : evt_{identity_a} column name.
    evt_col_b  : evt_{identity_b} column name.

    Returns
    -------
    pd.DataFrame
        One row per entity with columns:
        entity_col, obs_start, obs_end, n_a, n_b, has_a, has_b, has_both
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

        stats = compute_entity_presence(dates_a, dates_b)
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = obs_start
        stats[obs_end_col]   = obs_end
        rows.append(stats)

    return pd.DataFrame(rows)
