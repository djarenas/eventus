"""
occurrence_event_analyzer_utils.py
Per-entity computation utilities for OccurrenceEventAnalyzer.
No window, no config — just nearest-neighbor gaps and within proportion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any


# ── Date parsers ──────────────────────────────────────────────────────────────

def _parse_dates(value: Any) -> list[pd.Timestamp]:
    """Parse a pipe-delimited date string into a sorted list of Timestamps."""
    if pd.isna(value) or not str(value).strip():
        return []
    dates = []
    for token in str(value).split(" | "):
        token = token.strip()
        if not token:
            continue
        try:
            dates.append(pd.Timestamp(token).normalize())
        except Exception:
            continue
    return sorted(dates)


def _parse_event_pairs(
    starts_val: Any,
    ends_val:   Any,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Parse pipe-delimited start and end strings into sorted (start, end) pairs.
    Pairs where start > end are dropped.
    """
    starts = _parse_dates(starts_val)
    ends   = _parse_dates(ends_val)
    if len(starts) != len(ends):
        return []
    return sorted(
        [(s, e) for s, e in zip(starts, ends) if s <= e],
        key=lambda x: x[0],
    )


# ── Within computation ────────────────────────────────────────────────────────

def _count_within(
    occ_dates: list[pd.Timestamp],
    evt_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> int:
    """Count occurrences that fall inside any event interval (inclusive)."""
    count = 0
    for occ in occ_dates:
        for start, end in evt_pairs:
            if start <= occ <= end:
                count += 1
                break  # count each occ once even if it falls in multiple events
    return count


# ── Gap computation ───────────────────────────────────────────────────────────

def _occ_to_next_event_gaps(
    occ_dates: list[pd.Timestamp],
    evt_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[float]:
    """
    For each occurrence, find the nearest event START strictly after it.
    Return list of gap days. One gap per occurrence that has a qualifying pair.
    """
    gaps = []
    for occ in occ_dates:
        future_starts = [
            (start - occ).days
            for start, _ in evt_pairs
            if start > occ
        ]
        if future_starts:
            gaps.append(float(min(future_starts)))
    return gaps


def _event_to_next_occ_gaps(
    occ_dates: list[pd.Timestamp],
    evt_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[float]:
    """
    For each event, find the nearest occurrence strictly after DISCHARGE (end).
    Return list of gap days. One gap per event that has a qualifying pair.
    """
    gaps = []
    for _, end in evt_pairs:
        future_occs = [
            (occ - end).days
            for occ in occ_dates
            if occ > end
        ]
        if future_occs:
            gaps.append(float(min(future_occs)))
    return gaps


def _gap_stats(gaps: list[float]) -> dict:
    """Compute mean, median, std. NaN if no gaps or insufficient for std."""
    if not gaps:
        return {"mean": np.nan, "median": np.nan, "std": np.nan}
    arr = np.array(gaps, dtype=float)
    return {
        "mean":   float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std":    float(np.std(arr, ddof=1)) if len(arr) >= 2 else np.nan,
    }


# ── Per-entity computation ────────────────────────────────────────────────────

def compute_entity_stats(
    occ_val:    Any,
    starts_val: Any,
    ends_val:   Any,
) -> dict:
    """
    Compute all OccurrenceEventResult statistics for one entity.

    Parameters
    ----------
    occ_val    : pipe-delimited occurrence dates string
    starts_val : pipe-delimited event start dates string
    ends_val   : pipe-delimited event end dates string
    """
    occ_dates = _parse_dates(occ_val)
    evt_pairs = _parse_event_pairs(starts_val, ends_val)

    n_occ_total    = len(occ_dates)
    n_events_total = len(evt_pairs)
    n_occ_within   = _count_within(occ_dates, evt_pairs)

    pct_occ_within = (
        round(100.0 * n_occ_within / n_occ_total, 2)
        if n_occ_total > 0 else np.nan
    )

    occ_to_evt_gaps = _occ_to_next_event_gaps(occ_dates, evt_pairs)
    evt_to_occ_gaps = _event_to_next_occ_gaps(occ_dates, evt_pairs)

    occ_to_evt = _gap_stats(occ_to_evt_gaps)
    evt_to_occ = _gap_stats(evt_to_occ_gaps)

    return {
        "n_occ_total":              n_occ_total,
        "n_events_total":           n_events_total,
        "n_occ_within":             n_occ_within,
        "pct_occ_within":           pct_occ_within,
        "mean_days_occ_to_event":   occ_to_evt["mean"],
        "median_days_occ_to_event": occ_to_evt["median"],
        "std_days_occ_to_event":    occ_to_evt["std"],
        "mean_days_event_to_occ":   evt_to_occ["mean"],
        "median_days_event_to_occ": evt_to_occ["median"],
        "std_days_event_to_occ":    evt_to_occ["std"],
    }


def compute_all_entities(
    data:          pd.DataFrame,
    entity_col:    str,
    occ_col:       str,
    evt_starts_col: str,
    evt_ends_col:  str,
    obs_start_col: str,
    obs_end_col:   str,
) -> pd.DataFrame:
    """
    Compute per-entity stats for all entities in the CohortTimeline data.
    Returns a DataFrame with one row per entity.
    """
    rows = []
    for _, row in data.iterrows():
        stats = compute_entity_stats(
            occ_val    = row[occ_col],
            starts_val = row[evt_starts_col],
            ends_val   = row[evt_ends_col],
        )
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = row[obs_start_col]
        stats[obs_end_col]   = row[obs_end_col]
        rows.append(stats)

    return pd.DataFrame(rows)
