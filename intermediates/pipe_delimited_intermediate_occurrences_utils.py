"""
pipe_delimited_intermediate_occurrences_utils.py
Utility functions for PipeDelimitedIntermediateOccurrences.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

_ERROR_PREFIX = "[pipe_delimited_intermediate_occurrences_utils] Error"


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _parse_occ_dates(value) -> list[pd.Timestamp]:
    """Parse a pipe-delimited date string into a sorted list of Timestamps."""
    if pd.isna(value):
        return []
    tokens = str(value).split(" | ")
    dates = []
    for t in tokens:
        try:
            dates.append(pd.Timestamp(t.strip()).normalize())
        except Exception:
            continue
    return sorted(dates)


def _inter_event_gaps(dates: list[pd.Timestamp]) -> list[float]:
    """Return list of gap sizes in days between consecutive dates."""
    if len(dates) < 2:
        return []
    return [(dates[i+1] - dates[i]).days for i in range(len(dates) - 1)]


def _burstiness(gaps: list[float]) -> float | None:
    """
    Burstiness index = (std - mean) / (std + mean).
    Ranges from -1 (perfectly regular) to 1 (maximally bursty).
    Returns None if fewer than 2 gaps.
    """
    if len(gaps) < 2:
        return None
    m = np.mean(gaps)
    s = np.std(gaps)
    if m + s == 0:
        return None
    return round(float((s - m) / (s + m)), 4)


def _cv(gaps: list[float]) -> float | None:
    """
    Coefficient of variation = std / mean.
    Measure of relative variability of inter-event times.
    Returns None if fewer than 2 gaps or mean is 0.
    """
    if len(gaps) < 2:
        return None
    m = np.mean(gaps)
    if m == 0:
        return None
    return round(float(np.std(gaps) / m), 4)


# --------------------------------------------------------------------------- #
# Per-identity analysis columns
# --------------------------------------------------------------------------- #

def _compute_occ_cols_for_identity(
    data: pd.DataFrame,
    entity_col: str,
    occ_col: str,
    span_end_col: str = "span_end",
    span_duration_col: str = "span_duration_days",
) -> pd.DataFrame:
    """
    Compute all analysis columns for one occ_* column.
    Returns a DataFrame indexed by entity with new columns.
    """
    identity = occ_col[4:]  # strip "occ_"

    results = []
    for _, row in data.iterrows():
        dates = _parse_occ_dates(row[occ_col])
        gaps  = _inter_event_gaps(dates)

        span_end  = pd.Timestamp(row[span_end_col]).normalize() if not pd.isna(row.get(span_end_col)) else None
        span_days = float(row[span_duration_col]) if not pd.isna(row.get(span_duration_col)) else None

        if not dates:
            results.append({
                entity_col:                           row[entity_col],
                f"occ_{identity}_count":              0,
                f"occ_{identity}_first":              pd.NA,
                f"occ_{identity}_last":               pd.NA,
                f"occ_{identity}_recency_days":       pd.NA,
                f"occ_{identity}_mean_gap_days":      pd.NA,
                f"occ_{identity}_std_gap_days":       pd.NA,
                f"occ_{identity}_min_gap_days":       pd.NA,
                f"occ_{identity}_max_gap_days":       pd.NA,
                f"occ_{identity}_density":            0.0,
                f"occ_{identity}_burstiness":         pd.NA,
                f"occ_{identity}_cv":                 pd.NA,
            })
            continue

        recency = (span_end - dates[-1]).days if span_end else pd.NA
        density = round(len(dates) / span_days, 6) if span_days and span_days > 0 else pd.NA

        results.append({
            entity_col:                          row[entity_col],
            f"occ_{identity}_count":             len(dates),
            f"occ_{identity}_first":             dates[0],
            f"occ_{identity}_last":              dates[-1],
            f"occ_{identity}_recency_days":      recency,
            f"occ_{identity}_mean_gap_days":     round(float(np.mean(gaps)), 2) if gaps else pd.NA,
            f"occ_{identity}_std_gap_days":      round(float(np.std(gaps)), 2)  if gaps else pd.NA,
            f"occ_{identity}_min_gap_days":      min(gaps)    if gaps else pd.NA,
            f"occ_{identity}_max_gap_days":      max(gaps)    if gaps else pd.NA,
            f"occ_{identity}_density":           density,
            f"occ_{identity}_burstiness":        _burstiness(gaps),
            f"occ_{identity}_cv":                _cv(gaps),
        })

    return pd.DataFrame(results).set_index(entity_col)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def compute_occ_analysis(
    data: pd.DataFrame,
    entity_col: str,
) -> pd.DataFrame:
    """
    Compute all analysis columns for all occ_* columns in the data.
    Called by PipeDelimitedIntermediateOccurrences.self_analyze().

    For each occ_{identity} column, adds:
    - occ_{identity}_count
    - occ_{identity}_first, occ_{identity}_last
    - occ_{identity}_recency_days
    - occ_{identity}_mean_gap_days, occ_{identity}_std_gap_days
    - occ_{identity}_min_gap_days, occ_{identity}_max_gap_days
    - occ_{identity}_density
    - occ_{identity}_burstiness
    - occ_{identity}_cv

    Parameters
    ----------
    data : pd.DataFrame
        Intermediate data with occ_* columns.
    entity_col : str
        Entity identifier column.

    Returns
    -------
    pd.DataFrame
        Original data with all analysis columns added.
    """
    occ_cols = [c for c in data.columns if c.startswith("occ_")
                and not any(c.startswith(f"occ_{x}_") for x in
                            [col[4:] for col in data.columns if col.startswith("occ_")])]

    # More robust: get base occ_* cols (no underscore after identity)
    all_occ = [c for c in data.columns if c.startswith("occ_")]
    # Filter to only the raw date columns (not already-analyzed cols)
    analyzed_suffixes = ("_count", "_first", "_last", "_recency_days",
                         "_mean_gap_days", "_std_gap_days", "_min_gap_days",
                         "_max_gap_days", "_density", "_burstiness", "_cv")
    base_occ_cols = [c for c in all_occ
                     if not any(c.endswith(s) for s in analyzed_suffixes)]

    if not base_occ_cols:
        raise ValueError(
            f"{_ERROR_PREFIX}: no occ_* columns found in data"
        )

    out = data.copy()
    for occ_col in base_occ_cols:
        analysis = _compute_occ_cols_for_identity(
            data, entity_col, occ_col,
            span_end_col="span_end",
            span_duration_col="span_duration_days",
        )
        for col in analysis.columns:
            out[col] = out[entity_col].map(analysis[col])

    return out.reset_index(drop=True)


def calc_occ_summary(
    data: pd.DataFrame,
    entity_col: str,
    percentiles: list[int] = [25, 50, 75],
) -> dict:
    """
    Build a summary dict for all occurrence identities in the data.

    Parameters
    ----------
    data : pd.DataFrame
        Analyzed intermediate data (after self_analyze()).
    entity_col : str
        Entity identifier column.
    percentiles : list[int]
        Percentiles to compute for continuous metrics.

    Returns
    -------
    dict
        Nested summary dict keyed by identity.
    """
    analyzed_suffixes = ("_count", "_first", "_last", "_recency_days",
                         "_mean_gap_days", "_std_gap_days", "_min_gap_days",
                         "_max_gap_days", "_density", "_burstiness", "_cv")
    base_occ_cols = [c for c in data.columns
                     if c.startswith("occ_") and
                     not any(c.endswith(s) for s in analyzed_suffixes)]

    n_total  = len(data)
    summary  = {}

    def _stats(s: pd.Series) -> dict:
        clean = s.dropna()
        if clean.empty:
            return {"mean": None, **{f"p{p}": None for p in percentiles}}
        result = {"mean": round(float(clean.mean()), 2)}
        for p in percentiles:
            result[f"p{p}"] = round(float(np.percentile(clean, p)), 2)
        return result

    for occ_col in base_occ_cols:
        identity = occ_col[4:]
        count_col = f"occ_{identity}_count"

        if count_col not in data.columns:
            continue

        counts     = data[count_col].fillna(0).astype(int)
        n_any      = int((counts > 0).sum())
        n_multiple = int((counts > 1).sum())

        entry = {
            "# denominator: total entities": None,
            "n_total":      n_total,
            "n_with_any":   {"n": n_any,      "pct": round(100 * n_any / n_total, 1) if n_total else 0.0},
            "n_with_multiple": {"n": n_multiple, "pct": round(100 * n_multiple / n_total, 1) if n_total else 0.0},
            "count_stats":  _stats(counts[counts > 0].astype(float)),
        }

        # Tier 2 — gap stats (only entities with >= 2 occurrences)
        mean_gap = data.get(f"occ_{identity}_mean_gap_days")
        if mean_gap is not None:
            entry["mean_gap_days"]      = _stats(mean_gap.dropna())
            entry["std_gap_days"]       = _stats(data[f"occ_{identity}_std_gap_days"].dropna())
            entry["min_gap_days"]       = _stats(data[f"occ_{identity}_min_gap_days"].dropna())
            entry["max_gap_days"]       = _stats(data[f"occ_{identity}_max_gap_days"].dropna())
            entry["density"]            = _stats(data[f"occ_{identity}_density"].dropna())

        # Tier 3 — burstiness, cv
        burst = data.get(f"occ_{identity}_burstiness")
        if burst is not None:
            entry["burstiness"] = _stats(burst.dropna())
            entry["cv"]         = _stats(data[f"occ_{identity}_cv"].dropna())

        summary[identity] = entry

    return summary
