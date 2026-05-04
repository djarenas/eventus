"""
occurrences_self_analyze_utils.py
Pure utility functions for PipeDelimitedFormatOccurrences.self_analyze().
No class state — only data inputs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any

_VALID_EXTRAS = {
    "mean_gap",
    "std_gap",
    "cv_gap",
    "min_gap",
    "max_gap",
    "burstiness",
    "memory",
    "density",
}


def validate_extras(extras) -> list[str]:
    """
    Validate and normalize the extras parameter.

    Parameters
    ----------
    extras : list[str] | str | None
        "all", a list of extra stat names, or None.

    Returns
    -------
    list[str]
        Validated list of extra stat names.
    """
    if extras is None:
        return []
    if extras == "all":
        return sorted(_VALID_EXTRAS)
    if isinstance(extras, str):
        extras = [extras]
    if not isinstance(extras, list):
        raise TypeError(
            f"[occurrences_self_analyze_utils] extras must be a list of "
            f"strings, 'all', or None, got {type(extras).__name__}"
        )
    unknown = set(extras) - _VALID_EXTRAS
    if unknown:
        raise ValueError(
            f"[occurrences_self_analyze_utils] Unknown extras: "
            f"{sorted(unknown)}. "
            f"Valid options: {sorted(_VALID_EXTRAS)}"
        )
    return list(extras)


def parse_pipe_delimited_dates(
    value:     Any,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> list[pd.Timestamp]:
    """
    Parse a pipe-delimited date string into a sorted list of Timestamps.
    Filters to within [obs_start, obs_end]. Returns [] if value is null.
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


def compute_default_stats(
    dates:     list[pd.Timestamp],
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> dict[str, Any]:
    """
    Compute the default set of statistics — always fast, always meaningful.
    Returns NaN for all stats if dates is empty.

    Returns
    -------
    dict with keys: n, first, last, time_to_first, recency_days
    """
    n = len(dates)
    if n == 0:
        return {
            "n":              0,
            "first":          pd.NaT,
            "last":           pd.NaT,
            "time_to_first":  np.nan,
            "recency_days":   np.nan,
        }
    return {
        "n":              n,
        "first":          dates[0],
        "last":           dates[-1],
        "time_to_first":  float((dates[0]  - obs_start).days),
        "recency_days":   float((obs_end   - dates[-1]).days),
    }


def compute_gap_stats(
    dates: list[pd.Timestamp],
) -> dict[str, Any]:
    """
    Compute gap statistics from a sorted list of occurrence dates.
    Returns NaN for all stats if fewer than 2 occurrences.

    Returns
    -------
    dict with keys: mean_gap, std_gap, cv_gap, min_gap, max_gap
    """
    if len(dates) < 2:
        return {
            "mean_gap": np.nan,
            "std_gap":  np.nan,
            "cv_gap":   np.nan,
            "min_gap":  np.nan,
            "max_gap":  np.nan,
        }
    gaps = np.array([(dates[i+1] - dates[i]).days
                     for i in range(len(dates) - 1)],
                    dtype=float)
    mean = gaps.mean()
    std  = gaps.std(ddof=1) if len(gaps) > 1 else np.nan
    cv   = std / mean if mean > 0 else np.nan
    return {
        "mean_gap": float(mean),
        "std_gap":  float(std),
        "cv_gap":   float(cv),
        "min_gap":  float(gaps.min()),
        "max_gap":  float(gaps.max()),
    }


def compute_burstiness(dates: list[pd.Timestamp]) -> float | None:
    """
    Compute Goh-Barabási burstiness coefficient B.
    Requires at least 3 occurrences (2 gaps). Returns NaN otherwise.

    B = (std - mean) / (std + mean)
    Range: -1 (regular) to +1 (maximally bursty)
    """
    if len(dates) < 3:
        return np.nan
    gaps = np.array([(dates[i+1] - dates[i]).days
                     for i in range(len(dates) - 1)],
                    dtype=float)
    mean = gaps.mean()
    std  = gaps.std(ddof=1)
    denom = std + mean
    if denom == 0:
        return np.nan
    return float((std - mean) / denom)


def compute_memory(dates: list[pd.Timestamp]) -> float | None:
    """
    Compute Goh-Barabási memory coefficient M.
    Requires at least 4 occurrences (3 gaps). Returns NaN otherwise.

    M = corr(gap_i, gap_{i+1})
    Range: -1 to +1
    M > 0 → long gaps follow long gaps
    M < 0 → long gaps follow short gaps
    """
    if len(dates) < 4:
        return np.nan
    gaps = np.array([(dates[i+1] - dates[i]).days
                     for i in range(len(dates) - 1)],
                    dtype=float)
    g1 = gaps[:-1]
    g2 = gaps[1:]
    if g1.std() == 0 or g2.std() == 0:
        return np.nan
    return float(np.corrcoef(g1, g2)[0, 1])


def compute_density(
    n:         int,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> float:
    """
    Compute occurrence density — occurrences per day in observation period.
    Returns NaN if period has zero length.
    """
    period_days = (obs_end - obs_start).days
    if period_days == 0:
        return np.nan
    return float(n / period_days)


def analyze_occurrence_column(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
    extras:    list[str],
) -> pd.DataFrame:
    """
    Compute all requested statistics for one occ_{identity} column.

    Parameters
    ----------
    series : pd.Series
        Pipe-delimited occurrence dates, one value per entity.
    obs_start : pd.Series
        Observation period start per entity.
    obs_end : pd.Series
        Observation period end per entity.
    extras : list[str]
        Extra statistics to compute beyond the defaults.

    Returns
    -------
    pd.DataFrame
        One row per entity, columns named for each statistic.
    """
    rows = []
    for val, s, e in zip(series, obs_start, obs_end):
        dates = parse_pipe_delimited_dates(val, s, e)
        row   = compute_default_stats(dates, s, e)

        # Extras
        if extras:
            gap_stats_needed = {"mean_gap","std_gap","cv_gap",
                                "min_gap","max_gap"} & set(extras)
            if gap_stats_needed:
                gap_stats = compute_gap_stats(dates)
                for k in gap_stats_needed:
                    row[k] = gap_stats[k]

            if "burstiness" in extras:
                row["burstiness"] = compute_burstiness(dates)

            if "memory" in extras:
                row["memory"] = compute_memory(dates)

            if "density" in extras:
                row["density"] = compute_density(len(dates), s, e)

        rows.append(row)

    return pd.DataFrame(rows)
