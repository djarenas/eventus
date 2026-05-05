"""
cohort_timeline_occurrence_analyzer_utils.py
All utilities for CohortTimelineOccurrenceAnalyzer — guards, per-entity
stats, and cohort-level summary.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any

_ERROR = "[CohortTimelineOccurrenceAnalyzer] Error"

_VALID_EXTRAS = {
    "mean_gap", "std_gap", "cv_gap", "min_gap", "max_gap",
    "burstiness", "memory", "density",
}

_ALL_STAT_SUFFIXES = (
    "_n", "_first", "_last", "_time_to_first", "_recency_days",
    "_mean_gap", "_std_gap", "_cv_gap", "_min_gap", "_max_gap",
    "_burstiness", "_memory", "_density",
)

# ------------------------------------------------------------------ #
# Guards
# ------------------------------------------------------------------ #

def require_obs_period(has_obs_period: bool) -> None:
    if not has_obs_period:
        raise ValueError(
            f"{_ERROR} CohortTimeline has no observation period. "
            f"obs_start and obs_end are required to compute occurrence stats."
        )

def require_identity_present(identity: str, occurrence_identities: list[str]) -> None:
    if identity not in occurrence_identities:
        raise ValueError(
            f"{_ERROR} identity '{identity}' not found in "
            f"occurrence_identities: {occurrence_identities}"
        )

def require_not_already_analyzed(identity: str, columns: list[str]) -> None:
    col = f"occ_{identity}_n"
    if col in columns:
        raise ValueError(
            f"{_ERROR} '{col}' already exists. "
            f"compute_stats() has already been run for identity "
            f"'{identity}'. Each identity is analyzed once."
        )

def require_stats_exist(identity: str, columns: list[str], method: str) -> None:
    col = f"occ_{identity}_n"
    if col not in columns:
        raise ValueError(
            f"{_ERROR} .{method}() requires '{col}'. "
            f"Call compute_stats() first."
        )

# ------------------------------------------------------------------ #
# extras validation
# ------------------------------------------------------------------ #

def validate_extras(extras) -> list[str]:
    if extras is None:
        return []
    if extras == "all":
        return sorted(_VALID_EXTRAS)
    if isinstance(extras, str):
        extras = [extras]
    if not isinstance(extras, list):
        raise TypeError(
            f"{_ERROR} extras must be a list, 'all', or None, "
            f"got {type(extras).__name__}"
        )
    unknown = set(extras) - _VALID_EXTRAS
    if unknown:
        raise ValueError(
            f"{_ERROR} Unknown extras: {sorted(unknown)}. "
            f"Valid: {sorted(_VALID_EXTRAS)}"
        )
    return list(extras)

# ------------------------------------------------------------------ #
# Per-entity stats
# ------------------------------------------------------------------ #

def _parse_dates(
    value:     Any,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> list[pd.Timestamp]:
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


def _compute_default_stats(
    dates:     list[pd.Timestamp],
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> dict:
    if not dates:
        return {"n": 0, "first": pd.NaT, "last": pd.NaT,
                "time_to_first": np.nan, "recency_days": np.nan}
    return {
        "n":             len(dates),
        "first":         dates[0],
        "last":          dates[-1],
        "time_to_first": float((dates[0] - obs_start).days),
        "recency_days":  float((obs_end  - dates[-1]).days),
    }


def _compute_gap_stats(dates: list[pd.Timestamp]) -> dict:
    if len(dates) < 2:
        return {"mean_gap": np.nan, "std_gap": np.nan, "cv_gap": np.nan,
                "min_gap": np.nan, "max_gap": np.nan}
    gaps = np.array([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)], dtype=float)
    mean = gaps.mean()
    std  = gaps.std(ddof=1) if len(gaps) > 1 else np.nan
    return {
        "mean_gap": float(mean),
        "std_gap":  float(std),
        "cv_gap":   float(std / mean) if mean > 0 else np.nan,
        "min_gap":  float(gaps.min()),
        "max_gap":  float(gaps.max()),
    }


def _compute_burstiness(dates: list[pd.Timestamp]) -> float:
    if len(dates) < 3:
        return np.nan
    gaps  = np.array([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)], dtype=float)
    mean, std = gaps.mean(), gaps.std(ddof=1)
    denom = std + mean
    return float((std - mean) / denom) if denom != 0 else np.nan


def _compute_memory(dates: list[pd.Timestamp]) -> float:
    if len(dates) < 4:
        return np.nan
    gaps = np.array([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)], dtype=float)
    g1, g2 = gaps[:-1], gaps[1:]
    if g1.std() == 0 or g2.std() == 0:
        return np.nan
    return float(np.corrcoef(g1, g2)[0, 1])


def _compute_density(n: int, obs_start: pd.Timestamp, obs_end: pd.Timestamp) -> float:
    period_days = (obs_end - obs_start).days
    return float(n / period_days) if period_days > 0 else np.nan


def analyze_occurrence_column(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
    extras:    list[str],
) -> pd.DataFrame:
    rows = []
    for val, s, e in zip(series, obs_start, obs_end):
        dates = _parse_dates(val, s, e)
        row   = _compute_default_stats(dates, s, e)

        if extras:
            gap_extras = {"mean_gap","std_gap","cv_gap","min_gap","max_gap"} & set(extras)
            if gap_extras:
                gap_stats = _compute_gap_stats(dates)
                for k in gap_extras:
                    row[k] = gap_stats[k]
            if "burstiness" in extras:
                row["burstiness"] = _compute_burstiness(dates)
            if "memory" in extras:
                row["memory"] = _compute_memory(dates)
            if "density" in extras:
                row["density"] = _compute_density(len(dates), s, e)

        rows.append(row)
    return pd.DataFrame(rows)

# ------------------------------------------------------------------ #
# Cohort-level summary
# ------------------------------------------------------------------ #

def _stats(series: pd.Series, percentiles: list[int]) -> dict:
    clean = series.dropna()
    if clean.empty:
        return {"mean": None, **{f"p{p}": None for p in percentiles}}
    return {
        "mean": round(float(clean.mean()), 2),
        **{f"p{p}": round(float(np.percentile(clean, p)), 2) for p in percentiles},
    }


def calc_occ_summary(
    data:        pd.DataFrame,
    entity_col:  str,
    percentiles: list[int] = [25, 50, 75],
) -> dict:
    base_occ_cols = [
        c for c in data.columns
        if c.startswith("occ_")
        and not any(c.endswith(s) for s in _ALL_STAT_SUFFIXES)
    ]
    if not base_occ_cols:
        raise ValueError(f"{_ERROR} no raw occ_* columns found.")

    n_total = len(data)
    summary = {}

    for occ_col in base_occ_cols:
        identity  = occ_col[4:]
        count_col = f"occ_{identity}_n"
        if count_col not in data.columns:
            continue

        counts     = data[count_col].fillna(0).astype(int)
        n_any      = int((counts > 0).sum())
        n_multiple = int((counts > 1).sum())

        entry = {
            "n_total":         n_total,
            "n_with_any":      {"n": n_any,      "pct": round(100*n_any/n_total, 1) if n_total else 0.0},
            "n_with_multiple": {"n": n_multiple, "pct": round(100*n_multiple/n_total, 1) if n_total else 0.0},
            "count_stats":     _stats(counts[counts > 0].astype(float), percentiles),
        }

        for stat, label in [
            ("_time_to_first", "time_to_first_days"),
            ("_recency_days",  "recency_days"),
            ("_mean_gap",      "mean_gap_days"),
            ("_std_gap",       "std_gap_days"),
            ("_min_gap",       "min_gap_days"),
            ("_max_gap",       "max_gap_days"),
            ("_cv_gap",        "cv_gap"),
            ("_density",       "density"),
            ("_burstiness",    "burstiness"),
            ("_memory",        "memory"),
        ]:
            col = f"occ_{identity}{stat}"
            if col in data.columns:
                entry[label] = _stats(data[col].dropna(), percentiles)

        summary[identity] = entry

    return summary
