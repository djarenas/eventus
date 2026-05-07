"""
event_coverage_violin_plotter_utils.py
Pure utility functions for EventCoverageViolinPlotter.
No class state — only data and config inputs.

Arrays and plot_order are always keyed by SHORT metric names
(e.g. 'active_days', 'inactive_days_before_first_event').
Full column name construction (evt_{identity}_*) is an internal
detail of the array-building functions only.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

_ERROR_PREFIX = "[EventCoverageViolinPlotter]"

_UNIT_DIVISORS: dict[str, float] = {
    "days":   1.0,
    "months": 30.44,
    "years":  365.25,
}


# ── Unit conversion ───────────────────────────────────────────────────────────

def resolve_divisor(units: str | None) -> float:
    """
    Return the divisor for converting days to the configured unit.
    Falls back to 1.0 (no conversion) for None or unrecognised units.
    """
    if units is None:
        return 1.0
    divisor = _UNIT_DIVISORS.get(units.lower())
    if divisor is None:
        warnings.warn(
            f"{_ERROR_PREFIX} unrecognised units {units!r} — "
            f"no unit conversion applied. "
            f"Known units: {sorted(_UNIT_DIVISORS)}",
            UserWarning, stacklevel=2,
        )
        return 1.0
    return divisor


def apply_unit_conversion(
    arrays:  dict[str, np.ndarray],
    divisor: float,
) -> dict[str, np.ndarray]:
    """Convert duration values from days to the configured unit."""
    if divisor == 1.0:
        return arrays
    return {k: v / divisor for k, v in arrays.items()}


# ── Array builders ────────────────────────────────────────────────────────────

def build_total_arrays(
    data:     pd.DataFrame,
    identity: str,
) -> tuple[list[str], dict[str, np.ndarray]]:
    """
    Build arrays for plot_total() — active vs inactive days.

    Both metrics include ALL entities — zero is valid and meaningful.

    Parameters
    ----------
    data : pd.DataFrame
        CohortTimeline data with coverage analysis columns present.
    identity : str
        Event identity — used to locate evt_{identity}_* columns.

    Returns
    -------
    plot_order : list[str]
        Short metric names in display order: ['active_days', 'inactive_days']
    arrays : dict[str, np.ndarray]
        Keyed by short metric name.
    """
    plot_order = ["active_days", "inactive_days"]
    arrays: dict[str, np.ndarray] = {}
    for short in plot_order:
        full_col      = f"evt_{identity}_{short}"
        arrays[short] = (
            pd.to_numeric(data[full_col], errors="coerce")
            .fillna(0)
            .to_numpy(dtype=np.float64)
        )
    return plot_order, arrays


def build_breakdown_arrays(
    data:           pd.DataFrame,
    identity:       str,
    breakdown_cols: list[str],
) -> tuple[list[str], dict[str, np.ndarray]]:
    """
    Build arrays for plot_inactive_breakdown().

    Each metric is filtered to entities where value > 0.

    Parameters
    ----------
    data : pd.DataFrame
        CohortTimeline data with coverage analysis columns present.
    identity : str
        Event identity — used to construct evt_{identity}_* column names.
    breakdown_cols : list[str]
        Short metric names in display order, e.g.
        ['inactive_days_before_first_event', 'inactive_days_after_last_event'].

    Returns
    -------
    plot_order : list[str]
        Short metric names in display order.
    arrays : dict[str, np.ndarray]
        Keyed by short metric name. Each array filtered to values > 0.
    """
    arrays:     dict[str, np.ndarray] = {}
    plot_order: list[str]             = []

    for short in breakdown_cols:
        full_col = f"evt_{identity}_{short}"
        plot_order.append(short)

        if full_col not in data.columns:
            warnings.warn(
                f"{_ERROR_PREFIX} column '{full_col}' not found in data — "
                f"skipping.",
                UserWarning, stacklevel=2,
            )
            arrays[short] = np.array([], dtype=np.float64)
            continue

        raw = data[full_col]
        num = pd.to_numeric(raw, errors="coerce")

        bad_mask = raw.notna() & num.isna()
        if bad_mask.any():
            examples = raw[bad_mask].astype(str).head(5).tolist()
            warnings.warn(
                f"{_ERROR_PREFIX} column '{full_col}' has {bad_mask.sum()} "
                f"non-numeric value(s); they were dropped. "
                f"Examples: {examples}",
                UserWarning, stacklevel=2,
            )

        arrays[short] = num[num > 0].to_numpy(dtype=np.float64)

    return plot_order, arrays


# ── Tick labels ───────────────────────────────────────────────────────────────

def build_tick_labels(
    plot_order: list[str],
    arrays:     dict[str, np.ndarray],
    n_total:    int,
    resolved:   dict,
) -> list[str]:
    """
    Build x-tick labels showing metric label, n, and % of cohort.

    Format: "Label\\n(n=234, 45.2%)"

    Parameters
    ----------
    plot_order : list[str]
        Short metric names in display order.
    arrays : dict[str, np.ndarray]
        Keyed by short metric name.
    n_total : int
        Total number of entities in the cohort.
    resolved : dict[str, CategoryConfig]
        From ArraysViolinConfig.resolve() — carries label per key.
    """
    labels = []
    for key in plot_order:
        n     = len(arrays[key])
        pct   = 100 * n / n_total if n_total > 0 else 0.0
        cat   = resolved.get(key)
        label = (cat.label if cat and cat.label else key)
        labels.append(f"{label}\n(n={n:,}, {pct:.1f}%)")
    return labels
