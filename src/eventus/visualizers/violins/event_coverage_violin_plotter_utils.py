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
    arrays = {}
    for short in plot_order:
        full_col = f"evt_{identity}_{short}"
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
        Short metric names from config, e.g.
        ['inactive_days_before_first_event', 'inactive_days_after_last_event'].

    Returns
    -------
    plot_order : list[str]
        Short metric names in display order.
    arrays : dict[str, np.ndarray]
        Keyed by short metric name. Each array filtered to values > 0.
    """
    arrays     = {}
    plot_order = []

    for short in breakdown_cols:
        full_col = f"evt_{identity}_{short}"
        plot_order.append(short)

        if full_col not in data.columns:
            warnings.warn(
                f"{_ERROR_PREFIX} column '{full_col}' not found in data — "
                f"skipping.",
                UserWarning,
                stacklevel=2,
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
                UserWarning,
                stacklevel=2,
            )

        arrays[short] = num[num > 0].to_numpy(dtype=np.float64)

    return plot_order, arrays


def build_tick_labels(
    plot_order: list[str],
    arrays:     dict[str, np.ndarray],
    n_total:    int,
    config,
) -> list[str]:
    """
    Build x-tick labels showing metric label, n, and % of cohort.

    Parameters
    ----------
    plot_order : list[str]
        Short metric names.
    arrays : dict[str, np.ndarray]
        Keyed by short metric name.
    n_total : int
        Total number of entities in the cohort.
    config : EventCoverageViolinConfig

    Format: "Label\\n(n=234, 45.2%)"
    """
    labels = []
    for key in plot_order:
        n       = len(arrays[key])
        pct     = 100 * n / n_total if n_total > 0 else 0.0
        cat_cfg = config.metrics.get(key)
        label   = cat_cfg.label if cat_cfg and cat_cfg.label else key
        labels.append(f"{label}\n(n={n:,}, {pct:.1f}%)")
    return labels


def apply_unit_conversion(
    arrays:  dict[str, np.ndarray],
    divisor: float,
) -> dict[str, np.ndarray]:
    """Convert duration values from days to the configured unit."""
    if divisor == 1.0:
        return arrays
    return {k: v / divisor for k, v in arrays.items()}


def compute_widths(
    arrays:     dict[str, np.ndarray],
    plot_order: list[str],
    max_width:  float = 0.8,
) -> dict[str, float]:
    """Scale violin widths linearly with n — area-proportional."""
    ns    = {k: len(arrays[k]) for k in plot_order}
    max_n = max(ns.values()) if ns else 1
    return {k: max_width * (ns[k] / max_n) for k in plot_order}


def draw_violins(
    ax,
    plot_order:  list[str],
    arrays:      dict[str, np.ndarray],
    widths:      dict[str, float],
    colors:      dict[str, str],
    show_box:    bool,
    show_points: bool,
    point_alpha: float,
    point_size:  float,
    pcfg,
) -> None:
    """
    Draw outline-only violins, optional jitter points, and optional
    percentile lines.

    All dicts (arrays, widths, colors) are keyed by short metric name.
    """
    from scipy.stats import gaussian_kde

    _ = show_box  # compatibility parameter
    _LS_MAP = {"dashed": "--", "dotted": ":", "solid": "-"}
    rng = np.random.default_rng(42)

    for i, key in enumerate(plot_order):
        values = np.asarray(arrays[key], dtype=np.float64)
        if len(values) == 0:
            continue

        color = colors.get(key, "#666666")
        w     = widths[key]

        if len(np.unique(values)) < 2:
            warnings.warn(
                f"{_ERROR_PREFIX} metric '{key}' has fewer than 2 distinct "
                f"values — drawing summary line only.",
                UserWarning, stacklevel=2,
            )
            y = float(np.median(values))
            ax.hlines(y, i - w/2, i + w/2, colors="#333333", linewidth=1.4, zorder=4)

            if show_points:
                jitter = rng.uniform(-w * 0.15, w * 0.15, size=len(values))
                ax.scatter(
                    i + jitter, values,
                    s=point_size ** 2, color=color,
                    alpha=point_alpha, zorder=3, linewidths=0,
                )
            continue

        kde    = gaussian_kde(values, bw_method="scott")
        y_grid = np.linspace(values.min(), values.max(), 200)
        dens   = kde(y_grid)
        max_d  = dens.max()
        scaled = (dens / max_d * w / 2) if max_d > 0 else np.zeros_like(dens)

        x_left  = i - scaled
        x_right = i + scaled

        ax.plot(x_left,  y_grid, color=color, linewidth=1.4, alpha=0.95)
        ax.plot(x_right, y_grid, color=color, linewidth=1.4, alpha=0.95)

        q50  = float(np.percentile(values, 50))
        vmin = float(values.min())
        vmax = float(values.max())

        ax.hlines(q50,  i - w/2,    i + w/2,    colors="#333333", linewidth=1.4, zorder=4)
        ax.vlines(i,    vmin,       vmax,        colors="#666666", linewidth=0.9, alpha=0.7, zorder=3)
        ax.hlines([vmin, vmax], i - w*0.18, i + w*0.18, colors="#666666", linewidth=1.0, zorder=4)

        if show_points:
            jitter = rng.uniform(-w * 0.2, w * 0.2, size=len(values))
            ax.scatter(
                i + jitter, values,
                s=point_size ** 2, color=color,
                alpha=point_alpha, zorder=3, linewidths=0,
            )

        if pcfg.show and len(values) > 0:
            ls  = _LS_MAP.get(pcfg.linestyle, "--")
            x_l = i - w / 2
            x_r = i + w / 2
            for p in pcfg.values:
                val = float(np.percentile(values, p))
                ax.hlines(
                    val, xmin=x_l, xmax=x_r,
                    colors=pcfg.color, linewidth=1.2,
                    linestyle=ls, zorder=4,
                )
                if pcfg.show_labels:
                    ax.text(
                        x_r + 0.02, val,
                        f"p{p}={val:.1f}",
                        fontsize=7, color=pcfg.color,
                        va="center", ha="left",
                    )
