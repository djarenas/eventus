"""
event_co_occurrence_gap_utils.py
Per-entity nearest-gap computation for
EventCoOccurrenceAnalyzer.compute_gaps().

Gap definition
--------------
For each A event, the nearest B event in either direction (before or
after) is found. The gap in absolute days is always non-negative.
The median across all A events for an entity is stored.
Same logic applies B→nearest A.

Design notes (future expansion)
---------------------------------
- Median chosen over mean — see EventCoOccurrenceGapSummary docstring.
- Per-entity summary chosen over all-pairs — see same docstring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.analyzers.event_cooccurrence.event_co_occurrence_primitives import (
    build_co_occurrence_streams,
)


def nearest_gaps(
    source: list,
    target: list,
) -> list[float]:
    """
    For each event in source, find the nearest target event in either
    direction. Return the absolute gap in days for each source event
    that has at least one target event.

    Parameters
    ----------
    source : Sorted list of source event timestamps.
    target : Sorted list of target event timestamps.

    Returns
    -------
    list[float]
        One absolute gap per source event. Empty if source or target
        is empty.
    """
    if not source or not target:
        return []
    gaps = []
    for s in source:
        distances = [abs((s - t).days) for t in target]
        gaps.append(float(min(distances)))
    return gaps


def compute_entity_gaps(
    dates_a: list,
    dates_b: list,
) -> dict:
    """
    Compute nearest-gap statistics for one entity.

    Parameters
    ----------
    dates_a : Sorted list of A event timestamps within obs window.
    dates_b : Sorted list of B event timestamps within obs window.

    Returns
    -------
    dict with keys:
        n_a, n_b,
        median_gap_a_to_nearest_b,
        median_gap_b_to_nearest_a
    """
    n_a = len(dates_a)
    n_b = len(dates_b)

    if n_a == 0 or n_b == 0:
        return {
            "n_a":                       n_a,
            "n_b":                       n_b,
            "median_gap_a_to_nearest_b": np.nan,
            "median_gap_b_to_nearest_a": np.nan,
        }

    gaps_a_to_b = nearest_gaps(dates_a, dates_b)
    gaps_b_to_a = nearest_gaps(dates_b, dates_a)

    return {
        "n_a":                       n_a,
        "n_b":                       n_b,
        "median_gap_a_to_nearest_b": float(np.median(gaps_a_to_b)) if gaps_a_to_b else np.nan,
        "median_gap_b_to_nearest_a": float(np.median(gaps_b_to_a)) if gaps_b_to_a else np.nan,
    }


def compute_gap_stats(
    data:       pd.DataFrame,
    entity_col: str,
    evt_col_a:  str,
    evt_col_b:  str,
) -> pd.DataFrame:
    """
    Compute nearest-gap statistics for all entities.

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
        entity_col, obs_start, obs_end,
        n_a, n_b,
        median_gap_a_to_nearest_b,
        median_gap_b_to_nearest_a,
        a_offsets, b_offsets
        (a_offsets / b_offsets are lists of event day-offsets from
        obs_start, used by the rotation and label-permutation nulls.)
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
        # Per-entity event day-offsets from obs_start. Retained so that
        # permutation-family null models (rotation, label permutation) can
        # resample the observed timings; the uniform Monte Carlo null does
        # not need them. Stored as plain lists (object dtype column).
        stats["a_offsets"]   = [float((d - obs_start).days) for d in dates_a]
        stats["b_offsets"]   = [float((d - obs_start).days) for d in dates_b]
        rows.append(stats)

    return pd.DataFrame(rows)
