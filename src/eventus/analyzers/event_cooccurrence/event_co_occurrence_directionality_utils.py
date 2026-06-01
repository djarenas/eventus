"""
event_co_occurrence_directionality_utils.py
Per-entity mean signed gap computation for
EventCoOccurrenceAnalyzer.compute_directionality().

Signed gap definition
---------------------
For each A event, find the nearest B event in either direction.
Record the signed gap: positive if B is after A, negative if before.
Take the mean across all A events for that entity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.analyzers.event_cooccurrence.event_co_occurrence_primitives import (
    build_co_occurrence_streams,
)


def signed_nearest_gaps(
    source: list,
    target: list,
) -> list[float]:
    """
    For each event in source, find the nearest target event in either
    direction. Return the signed gap in days for each source event.

    Positive = nearest target is after source (source precedes target).
    Negative = nearest target is before source (target precedes source).
    Zero     = nearest target is on the same day.

    Parameters
    ----------
    source : Sorted list of source event timestamps.
    target : Sorted list of target event timestamps.

    Returns
    -------
    list[float]
        One signed gap per source event. Empty if source or target empty.
    """
    if not source or not target:
        return []

    gaps = []
    for s in source:
        distances = [(t - s).days for t in target]
        # Find the nearest by absolute distance
        nearest = min(distances, key=abs)
        gaps.append(float(nearest))
    return gaps


def compute_entity_directionality(
    dates_a: list,
    dates_b: list,
) -> dict:
    """
    Compute mean signed gap for one entity.

    Parameters
    ----------
    dates_a : Sorted list of A event timestamps within obs window.
    dates_b : Sorted list of B event timestamps within obs window.

    Returns
    -------
    dict with keys: n_a, n_b, mean_signed_gap
    """
    n_a = len(dates_a)
    n_b = len(dates_b)

    if n_a == 0 or n_b == 0:
        return {
            "n_a":             n_a,
            "n_b":             n_b,
            "mean_signed_gap": np.nan,
        }

    signed_gaps = signed_nearest_gaps(dates_a, dates_b)

    return {
        "n_a":             n_a,
        "n_b":             n_b,
        "mean_signed_gap": float(np.mean(signed_gaps)) if signed_gaps else np.nan,
    }


def compute_directionality_stats(
    data:       pd.DataFrame,
    entity_col: str,
    evt_col_a:  str,
    evt_col_b:  str,
) -> pd.DataFrame:
    """
    Compute mean signed gap statistics for all entities.

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
        entity_col, obs_start, obs_end, n_a, n_b, mean_signed_gap
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

        stats = compute_entity_directionality(dates_a, dates_b)
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = obs_start
        stats[obs_end_col]   = obs_end
        rows.append(stats)

    return pd.DataFrame(rows)
