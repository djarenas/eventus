"""
events_within_obs_period_violin_plotter_utils.py
Pure utility functions for EventsWithinObsPeriodViolinPlotter.
No class state — only data and config inputs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

_ERROR_PREFIX = "[EventsWithinObsPeriodViolinPlotter]"


def build_total_arrays(  
    data: pd.DataFrame,  
) -> tuple[list[str], dict[str, np.ndarray]]:  
    plot_order = ["active_days", "inactive_days"]  
    arrays = {  
        col: pd.to_numeric(data[col], errors="coerce").fillna(0).to_numpy(dtype=np.float64)  
        for col in plot_order  
    }  
    return plot_order, arrays  

def build_breakdown_arrays(  
    data: pd.DataFrame,  
    breakdown_cols: list[str],  
) -> tuple[list[str], dict[str, np.ndarray]]:  
    """  
    Build arrays for plot_inactive_breakdown() — each metric filtered  
    to entities where value > 0. Non-numeric values are coerced to NaN.  
    """  
    import warnings  
  
    arrays = {}  
    for col in breakdown_cols:  
        raw = data[col]  
        num = pd.to_numeric(raw, errors="coerce")  # <-- key fix  
  
        bad_mask = raw.notna() & num.isna()  
        if bad_mask.any():  
            examples = raw[bad_mask].astype(str).head(5).tolist()  
            warnings.warn(  
                f"{_ERROR_PREFIX} column '{col}' has {bad_mask.sum()} non-numeric "  
                f"value(s); they were dropped. Examples: {examples}",  
                UserWarning,  
                stacklevel=2,  
            )  
  
        arrays[col] = num[num > 0].to_numpy(dtype=np.float64)  
  
    return breakdown_cols, arrays  


def build_tick_labels(
    plot_order: list[str],
    arrays:     dict[str, np.ndarray],
    n_total:    int,
    config,                              # EventsWithinObsPeriodViolinConfig
) -> list[str]:
    """
    Build x-tick labels showing metric label, n, and % of cohort.

    Format: "Label\n(n=234, 45.2%)"

    Parameters
    ----------
    plot_order : list[str]
    arrays : dict[str, np.ndarray]
    n_total : int
        Total cohort size — denominator for percentage.
    config : EventsWithinObsPeriodViolinConfig

    Returns
    -------
    list[str]
    """
    labels = []
    for col in plot_order:
        n       = len(arrays[col])
        pct     = 100 * n / n_total if n_total > 0 else 0.0
        cat_cfg = config.metrics.get(col)
        label   = cat_cfg.label if cat_cfg and cat_cfg.label else col
        labels.append(f"{label}\n(n={n:,}, {pct:.1f}%)")
    return labels


def apply_unit_conversion(
    arrays:  dict[str, np.ndarray],
    divisor: float,
) -> dict[str, np.ndarray]:
    """
    Convert duration values from days to the configured unit.

    Parameters
    ----------
    arrays : dict[str, np.ndarray]
    divisor : float
        1.0 = days, 30.44 = months, 365.25 = years.

    Returns
    -------
    dict[str, np.ndarray]
        New dict with converted values. Original unchanged.
    """
    if divisor == 1.0:
        return arrays
    return {k: v / divisor for k, v in arrays.items()}


def compute_widths(
    arrays:     dict[str, np.ndarray],
    plot_order: list[str],
    max_width:  float = 0.8,
) -> dict[str, float]:
    """
    Scale violin widths linearly with n — area-proportional.
    """
    ns    = {k: len(arrays[k]) for k in plot_order}
    max_n = max(ns.values()) if ns else 1
    return {k: max_width * (ns[k] / max_n) for k in plot_order}


def draw_violins(  
    ax,  
    plot_order:  list[str],  
    arrays:      dict[str, np.ndarray],  
    widths:      dict[str, float],  
    colors:      dict[str, str],  
    show_box:    bool,      # kept for compatibility; intentionally ignored  
    show_points: bool,  
    point_alpha: float,  
    point_size:  float,  
    pcfg,  
) -> None:  
    """  
    Draw outline-only violins (no fill), optional jitter points, and optional  
    percentile lines. No IQR rectangle boxes.  
    """  
    import warnings  
    from scipy.stats import gaussian_kde  
  
    _ = show_box  # compatibility with existing caller  
    _LS_MAP = {"dashed": "--", "dotted": ":", "solid": "-"}  
    rng = np.random.default_rng(42)  # one RNG for whole plot  
  
    for i, key in enumerate(plot_order):  
        values = np.asarray(arrays[key], dtype=np.float64)  
        if len(values) == 0:  
            continue  
  
        color = colors.get(key, "#666666")  
        w = widths[key]  
  
        # If constant/near-constant, draw a simple marker instead of KDE violin  
        if len(np.unique(values)) < 2:  
            warnings.warn(  
                f"[EventsWithinObsPeriodViolinPlotter] category '{key}' has "  
                f"fewer than 2 distinct values — drawing summary line only.",  
                UserWarning, stacklevel=2,  
            )  
            y = float(np.median(values))  
            ax.hlines(y, i - w/2, i + w/2, colors="#333333", linewidth=1.4, zorder=4)  
  
            if show_points:  
                jitter = rng.uniform(-w * 0.15, w * 0.15, size=len(values))  
                ax.scatter(  
                    i + jitter, values,  
                    s=point_size ** 2, color=color,  
                    alpha=point_alpha, zorder=3, linewidths=0  
                )  
            continue  
  
        # KDE-based violin outline  
        kde = gaussian_kde(values, bw_method="scott")  
        y_grid = np.linspace(values.min(), values.max(), 200)  
        dens = kde(y_grid)  
        max_d = dens.max()  
        scaled = (dens / max_d * w / 2) if max_d > 0 else np.zeros_like(dens)  
  
        x_left = i - scaled  
        x_right = i + scaled  
  
        # OUTLINE ONLY (no fill_betweenx)  
        ax.plot(x_left, y_grid, color=color, linewidth=1.4, alpha=0.95)  
        ax.plot(x_right, y_grid, color=color, linewidth=1.4, alpha=0.95)  
  
        # Median + min/max "extrema" styling (clean, old-school)  
        q50 = float(np.percentile(values, 50))  
        vmin, vmax = float(values.min()), float(values.max())  
  
        ax.hlines(q50, i - w/2, i + w/2, colors="#333333", linewidth=1.4, zorder=4)  
        ax.vlines(i, vmin, vmax, colors="#666666", linewidth=0.9, alpha=0.7, zorder=3)  
        ax.hlines([vmin, vmax], i - w*0.18, i + w*0.18, colors="#666666", linewidth=1.0, zorder=4)  
  
        if show_points:  
            jitter = rng.uniform(-w * 0.2, w * 0.2, size=len(values))  
            ax.scatter(  
                i + jitter, values,  
                s=point_size ** 2, color=color,  
                alpha=point_alpha, zorder=3, linewidths=0,  
            )  
  
        # Optional percentile lines  
        if pcfg.show and len(values) > 0:  
            ls = _LS_MAP.get(pcfg.linestyle, "--")  
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