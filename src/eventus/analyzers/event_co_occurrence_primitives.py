"""
event_co_occurrence_primitives.py
Shared primitive operations for EventCoOccurrenceAnalyzer utils.

Functions
---------
parse_event_dates(value, obs_start, obs_end)
    Parse a pipe-delimited event date string into a sorted list of
    pd.Timestamps, filtered to the obs window. Same contract as
    event_primitives_utils.parse_dates — duplicated here to keep
    co-occurrence utils self-contained with no cross-analyzer imports.

build_co_occurrence_streams(row, evt_col_a, evt_col_b, obs_start, obs_end)
    Parse both event columns for one entity and return two sorted
    date lists filtered to the obs window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any


# ── Date parser ───────────────────────────────────────────────────────────────

def parse_event_dates(
    value:     Any,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> list[pd.Timestamp]:
    """
    Parse a pipe-delimited event date string into a sorted list of
    pd.Timestamps, retaining only dates within [obs_start, obs_end].

    Parameters
    ----------
    value : Any
        Raw cell value from an evt_{identity} column.
        Expected format: "2020-01-01 | 2020-06-15 | 2021-03-10"
        NaN / None returns an empty list.
    obs_start : pd.Timestamp
        Observation period start (inclusive), normalized to midnight.
    obs_end : pd.Timestamp
        Observation period end (inclusive), normalized to midnight.

    Returns
    -------
    list[pd.Timestamp]
        Sorted list of valid timestamps within the obs window.
        Empty if value is NaN or no dates fall within the window.
    """
    if pd.isna(value):
        return []
    dates = []
    for token in str(value).split(" | "):
        try:
            ts = pd.Timestamp(token.strip()).normalize()
            if obs_start <= ts <= obs_end:
                dates.append(ts)
        except Exception:
            continue
    return sorted(dates)


# ── Stream builder ────────────────────────────────────────────────────────────

def build_co_occurrence_streams(
    row:        pd.Series,
    evt_col_a:  str,
    evt_col_b:  str,
    obs_start:  pd.Timestamp,
    obs_end:    pd.Timestamp,
) -> tuple[list[pd.Timestamp], list[pd.Timestamp]]:
    """
    Parse both event columns for one entity and return two sorted
    date lists filtered to the obs window.

    Parameters
    ----------
    row       : One row from CohortTimeline.data.
    evt_col_a : Column name for identity A, e.g. "evt_ed_visit".
    evt_col_b : Column name for identity B, e.g. "evt_specialist_referral".
    obs_start : Entity's observation period start.
    obs_end   : Entity's observation period end.

    Returns
    -------
    tuple[list[pd.Timestamp], list[pd.Timestamp]]
        (dates_a, dates_b) — both sorted, both filtered to obs window.
    """
    dates_a = parse_event_dates(row.get(evt_col_a), obs_start, obs_end)
    dates_b = parse_event_dates(row.get(evt_col_b), obs_start, obs_end)
    return dates_a, dates_b


# ── Gap helpers ───────────────────────────────────────────────────────────────

def nearest_forward_gaps(
    source: list[pd.Timestamp],
    target: list[pd.Timestamp],
) -> list[float]:
    """
    For each event in source, find the nearest target event that occurs
    strictly after it. Return the gap in days for each qualifying pair.

    Parameters
    ----------
    source : Sorted list of source event timestamps.
    target : Sorted list of target event timestamps.

    Returns
    -------
    list[float]
        One gap per source event that has a qualifying target after it.
        Empty if no qualifying pairs exist.
    """
    gaps = []
    for s in source:
        future = [t for t in target if t > s]
        if future:
            gaps.append(float((min(future) - s).days))
    return gaps


def gap_stats(gaps: list[float]) -> dict:
    """
    Compute mean, median, std from a list of gap values.

    Returns
    -------
    dict with keys: mean, median, std
        All NaN if gaps is empty. std is NaN if fewer than 2 gaps.
    """
    if not gaps:
        return {"mean": np.nan, "median": np.nan, "std": np.nan}
    arr = np.array(gaps, dtype=float)
    return {
        "mean":   float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std":    float(np.std(arr, ddof=1)) if len(arr) >= 2 else np.nan,
    }
