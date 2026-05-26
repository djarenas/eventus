"""
event_stats_utils.py
Per-entity event stat computation for CohortTimelineEventAnalyzer.
Imports primitives from event_primitives_utils.

Functions
---------
compute_volume_stats(series, obs_start, obs_end)
    Per-entity event counts.

compute_timing_stats(series, obs_start, obs_end, max_n)
    Per-entity timing of the nth event and recency.

compute_shape_stats(series, obs_start, obs_end)
    Per-entity behavioral fingerprint over the full date list.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .event_primitives_utils import parse_dates, compute_gaps


# ------------------------------------------------------------------ #
# Volume
# ------------------------------------------------------------------ #

def _volume_row(dates: list) -> dict:
    return {"n": len(dates)}


def compute_volume_stats(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
) -> pd.DataFrame:
    """
    Compute per-entity event counts.

    Parameters
    ----------
    series : pd.Series
        Raw evt_{identity} column (pipe-delimited date strings).
    obs_start : pd.Series
        Per-entity observation period start timestamps.
    obs_end : pd.Series
        Per-entity observation period end timestamps.

    Returns
    -------
    pd.DataFrame
        One row per entity. Columns: n (int).
    """
    rows = []
    for val, s, e in zip(series, obs_start, obs_end):
        dates = parse_dates(val, s, e)
        rows.append(_volume_row(dates))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ #
# Timing
# ------------------------------------------------------------------ #

def _timing_row(
    dates:     list,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
    max_n:     int,
) -> dict:
    row = {}
    for nth in range(1, max_n + 1):
        if len(dates) >= nth:
            row[f"time_to_{nth}"] = float((dates[nth - 1] - obs_start).days)
        else:
            row[f"time_to_{nth}"] = np.nan
    row["recency_days"] = (
        float((obs_end - dates[-1]).days) if dates else np.nan
    )
    return row


def compute_timing_stats(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
    max_n:     int,
) -> pd.DataFrame:
    """
    Compute per-entity timing of the nth event relative to obs_start,
    up to max_n, plus recency_days.

    Parameters
    ----------
    series : pd.Series
        Raw evt_{identity} column (pipe-delimited date strings).
    obs_start : pd.Series
        Per-entity observation period start timestamps.
    obs_end : pd.Series
        Per-entity observation period end timestamps.
    max_n : int
        Maximum nth event to compute timing for. Must be >= 1.
        Validated upstream by the analyzer — not re-validated here.

    Returns
    -------
    pd.DataFrame
        One row per entity.
        Columns: time_to_1, ..., time_to_{max_n} (float), recency_days (float).
        NaN where entity has fewer events than nth.
        recency_days is NaN for entities with zero events.
    """
    rows = []
    for val, s, e in zip(series, obs_start, obs_end):
        dates = parse_dates(val, s, e)
        rows.append(_timing_row(dates, s, e, max_n))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ #
# Shape
# ------------------------------------------------------------------ #

def _shape_row(
    dates:     list,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> dict:
    n    = len(dates)
    gaps = compute_gaps(dates)

    # gap-based stats — require n >= 2 for gaps to exist
    if n >= 2:
        mean_gap = float(gaps.mean())
        min_gap  = float(gaps.min())
        max_gap  = float(gaps.max())
    else:
        mean_gap = min_gap = max_gap = np.nan

    # std and cv — require at least 2 gaps (n >= 3) for ddof=1
    if n >= 3:
        std_gap = float(gaps.std(ddof=1))
        cv_gap  = float(std_gap / mean_gap) if mean_gap > 0 else np.nan
    else:
        std_gap = cv_gap = np.nan

    # burstiness — requires n >= 3 (at least 2 gaps for std)
    if n >= 3:
        denom      = std_gap + mean_gap
        burstiness = float((std_gap - mean_gap) / denom) if denom != 0 else np.nan
    else:
        burstiness = np.nan

    # memory — requires n >= 4 (at least 3 gaps for lag-1 autocorrelation)
    if n >= 4:
        g1 = gaps[:-1]
        g2 = gaps[1:]
        if g1.std() == 0 or g2.std() == 0:
            memory = np.nan
        else:
            memory = float(np.corrcoef(g1, g2)[0, 1])
    else:
        memory = np.nan

    # density — requires n >= 1 and obs_duration > 0
    period_days = (obs_end - obs_start).days
    density = float(n / period_days) if (n >= 1 and period_days > 0) else np.nan

    # center_of_mass — requires n >= 1 and obs_duration > 0
    # weighted average day of event, normalized to [0, 1]
    # 0 = all at obs_start, 1 = all at obs_end, 0.5 = evenly spread
    if n >= 1 and period_days > 0:
        day_offsets   = np.array([(d - obs_start).days for d in dates], dtype=float)
        center_of_mass = float(day_offsets.mean() / period_days)
    else:
        center_of_mass = np.nan

    return {
        "mean_gap":       mean_gap,
        "std_gap":        std_gap,
        "cv_gap":         cv_gap,
        "min_gap":        min_gap,
        "max_gap":        max_gap,
        "burstiness":     burstiness,
        "memory":         memory,
        "density":        density,
        "center_of_mass": center_of_mass,
    }


def compute_shape_stats(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
) -> pd.DataFrame:
    """
    Compute per-entity behavioral fingerprint over the full date list.

    Parameters
    ----------
    series : pd.Series
        Raw evt_{identity} column (pipe-delimited date strings).
    obs_start : pd.Series
        Per-entity observation period start timestamps.
    obs_end : pd.Series
        Per-entity observation period end timestamps.

    Returns
    -------
    pd.DataFrame
        One row per entity. Columns:
        mean_gap, std_gap, cv_gap, min_gap, max_gap (float) — require n >= 2/3
        burstiness (float) — requires n >= 3
        memory (float)     — requires n >= 4
        density (float)    — requires n >= 1, obs_duration > 0
        center_of_mass (float) — requires n >= 1, obs_duration > 0
        NaN where minimum event threshold is not met.
    """
    rows = []
    for val, s, e in zip(series, obs_start, obs_end):
        dates = parse_dates(val, s, e)
        rows.append(_shape_row(dates, s, e))
    return pd.DataFrame(rows)
