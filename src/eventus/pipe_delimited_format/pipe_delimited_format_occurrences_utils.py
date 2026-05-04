"""
pipe_delimited_format_occurrences_utils.py
Utility functions for PipeDelimitedFormatOccurrences.

Note: per-occurrence statistics (burstiness, gap stats etc.) are computed
by occurrences_self_analyze_utils.py via self_analyze().
This module provides the cohort-level summary after self_analyze() has run.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

_ERROR_PREFIX = "[pipe_delimited_format_occurrences_utils] Error"

# Column suffixes produced by self_analyze() defaults
_DEFAULT_SUFFIXES = ("_n", "_first", "_last", "_time_to_first", "_recency_days")

# All suffixes produced by self_analyze() including extras
_ALL_SUFFIXES = _DEFAULT_SUFFIXES + (
    "_mean_gap", "_std_gap", "_cv_gap", "_min_gap", "_max_gap",
    "_burstiness", "_memory", "_density",
)


def calc_occ_summary(
    data:        pd.DataFrame,
    entity_col:  str,
    percentiles: list[int] = [25, 50, 75],
) -> dict:
    """
    Build a cohort-level summary dict for all occurrence identities.

    Requires self_analyze() to have been called first — looks for columns
    produced by self_analyze() such as occ_{identity}_n, occ_{identity}_first,
    occ_{identity}_burstiness, etc.

    Parameters
    ----------
    data : pd.DataFrame
        Analyzed intermediate data — after self_analyze().
    entity_col : str
        Entity identifier column.
    percentiles : list[int]
        Percentiles to compute for continuous metrics.

    Returns
    -------
    dict
        Nested summary dict keyed by identity.

    Raises
    ------
    ValueError
        If self_analyze() has not been called (no _n columns found).
    """
    # Find raw occ_ columns (no suffix)
    base_occ_cols = [
        c for c in data.columns
        if c.startswith("occ_")
        and not any(c.endswith(s) for s in _ALL_SUFFIXES)
    ]

    if not base_occ_cols:
        raise ValueError(
            f"{_ERROR_PREFIX}: no raw occ_* columns found. "
            f"Make sure the intermediate was produced by "
            f"OccurrencesWithinObsPeriodsAnalyzer."
        )

    # Check that self_analyze() has been called
    first_identity = base_occ_cols[0][4:]
    if f"occ_{first_identity}_n" not in data.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: occ_{first_identity}_n not found. "
            f"Call self_analyze() before print_summary() or save_summary()."
        )

    n_total = len(data)
    summary = {}

    def _stats(s: pd.Series) -> dict:
        clean = s.dropna()
        if clean.empty:
            return {"mean": None, **{f"p{p}": None for p in percentiles}}
        result = {"mean": round(float(clean.mean()), 2)}
        for p in percentiles:
            result[f"p{p}"] = round(float(np.percentile(clean, p)), 2)
        return result

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
            "n_with_any":      {
                "n":   n_any,
                "pct": round(100 * n_any / n_total, 1) if n_total else 0.0,
            },
            "n_with_multiple": {
                "n":   n_multiple,
                "pct": round(100 * n_multiple / n_total, 1) if n_total else 0.0,
            },
            "count_stats":     _stats(counts[counts > 0].astype(float)),
        }

        # Timing stats — from defaults
        for stat, label in [
            ("_time_to_first", "time_to_first_days"),
            ("_recency_days",  "recency_days"),
        ]:
            col = f"occ_{identity}{stat}"
            if col in data.columns:
                entry[label] = _stats(data[col].dropna())

        # Gap stats — from extras
        for stat, label in [
            ("_mean_gap", "mean_gap_days"),
            ("_std_gap",  "std_gap_days"),
            ("_min_gap",  "min_gap_days"),
            ("_max_gap",  "max_gap_days"),
            ("_cv_gap",   "cv_gap"),
            ("_density",  "density"),
        ]:
            col = f"occ_{identity}{stat}"
            if col in data.columns:
                entry[label] = _stats(data[col].dropna())

        # Burstiness and memory — from extras
        for stat, label in [
            ("_burstiness", "burstiness"),
            ("_memory",     "memory"),
        ]:
            col = f"occ_{identity}{stat}"
            if col in data.columns:
                entry[label] = _stats(data[col].dropna())

        summary[identity] = entry

    return summary
