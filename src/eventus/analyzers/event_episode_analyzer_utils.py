"""
event_episode_analyzer_utils.py
Per-entity computation utilities for EventEpisodeAnalyzer.
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


def _parse_episode_pairs(
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
    evt_dates: list[pd.Timestamp],
    eps_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> int:
    """Count events that fall inside any episode interval (inclusive)."""
    count = 0
    for occ in evt_dates:
        for start, end in eps_pairs:
            if start <= occ <= end:
                count += 1
                break  # count each occ once even if it falls in multiple episodes
    return count


# ── Gap computation ───────────────────────────────────────────────────────────

def _evt_to_next_episode_gaps(
    evt_dates: list[pd.Timestamp],
    eps_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[float]:
    """
    For each event, find the nearest episode START strictly after it.
    Return list of gap days. One gap per event that has a qualifying pair.
    """
    gaps = []
    for occ in evt_dates:
        future_starts = [
            (start - occ).days
            for start, _ in eps_pairs
            if start > occ
        ]
        if future_starts:
            gaps.append(float(min(future_starts)))
    return gaps


def _episode_to_next_evt_gaps(
    evt_dates: list[pd.Timestamp],
    eps_pairs: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[float]:
    """
    For each episode, find the nearest event strictly after DISCHARGE (end).
    Return list of gap days. One gap per episode that has a qualifying pair.
    """
    gaps = []
    for _, end in eps_pairs:
        future_occs = [
            (occ - end).days
            for occ in evt_dates
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
    evt_val:    Any,
    starts_val: Any,
    ends_val:   Any,
) -> dict:
    """
    Compute all EventEpisodeResult statistics for one entity.

    Parameters
    ----------
    evt_val    : pipe-delimited event dates string
    starts_val : pipe-delimited episode start dates string
    ends_val   : pipe-delimited episode end dates string
    """
    evt_dates = _parse_dates(evt_val)
    eps_pairs = _parse_episode_pairs(starts_val, ends_val)

    n_evt_total    = len(evt_dates)
    n_episodes_total = len(eps_pairs)
    n_evt_within   = _count_within(evt_dates, eps_pairs)

    pct_evt_within = (
        round(100.0 * n_evt_within / n_evt_total, 2)
        if n_evt_total > 0 else np.nan
    )

    evt_to_eps_gaps = _evt_to_next_episode_gaps(evt_dates, eps_pairs)
    eps_to_evt_gaps = _episode_to_next_evt_gaps(evt_dates, eps_pairs)

    evt_to_evt = _gap_stats(evt_to_eps_gaps)
    eps_to_occ = _gap_stats(eps_to_evt_gaps)

    return {
        "n_evt_total":              n_evt_total,
        "n_episodes_total":           n_episodes_total,
        "n_evt_within":             n_evt_within,
        "pct_evt_within":           pct_evt_within,
        "mean_days_evt_to_episode":   evt_to_evt["mean"],
        "median_days_evt_to_episode": evt_to_evt["median"],
        "std_days_evt_to_episode":    evt_to_evt["std"],
        "mean_days_episode_to_occ":   eps_to_occ["mean"],
        "median_days_episode_to_occ": eps_to_occ["median"],
        "std_days_episode_to_occ":    eps_to_occ["std"],
    }


def compute_all_entities(
    data:          pd.DataFrame,
    entity_col:    str,
    evt_col:       str,
    eps_starts_col: str,
    eps_ends_col:  str,
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
            evt_val    = row[evt_col],
            starts_val = row[eps_starts_col],
            ends_val   = row[eps_ends_col],
        )
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = row[obs_start_col]
        stats[obs_end_col]   = row[obs_end_col]
        rows.append(stats)

    return pd.DataFrame(rows)
