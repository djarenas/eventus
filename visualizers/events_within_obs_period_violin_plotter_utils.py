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
    """
    Build arrays for plot_total() — active_days and inactive_days,
    all entities, NA filled with 0.

    Parameters
    ----------
    data : pd.DataFrame
        Must contain active_days and inactive_days columns.

    Returns
    -------
    plot_order : list[str]
    arrays : dict[str, np.ndarray]
    """
    plot_order = ["active_days", "inactive_days"]
    arrays     = {col: data[col].fillna(0).to_numpy(dtype=np.float64) for col in plot_order}
    return plot_order, arrays


def build_breakdown_arrays(
    data:       pd.DataFrame,
    breakdown_cols: list[str],
) -> tuple[list[str], dict[str, np.ndarray]]:
    """
    Build arrays for plot_inactive_breakdown() — each metric filtered
    to entities where value > 0.

    Parameters
    ----------
    data : pd.DataFrame
        Must contain the breakdown columns.
    breakdown_cols : list[str]
        Ordered list of column names to include.

    Returns
    -------
    plot_order : list[str]
    arrays : dict[str, np.ndarray]
    """
    arrays = {}
    for col in breakdown_cols:
        vals        = data[col].dropna()
        arrays[col] = vals[vals > 0].to_numpy(dtype=np.float64)
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
    show_box:    bool,
    show_points: bool,
    point_alpha: float,
    point_size:  float,
    pcfg,
) -> None:
    """
    Draw all violins — one ax.violinplot call per violin.
    Per-violin percentile lines computed from each violin's own data.
    """
    import warnings
    _LS_MAP = {"dashed": "--", "dotted": ":", "solid": "-"}

    for i, key in enumerate(plot_order):
        values = arrays[key]
        if len(values) == 0:
            continue
        if len(np.unique(values)) < 2:
            warnings.warn(
                f"[EventsWithinObsPeriodViolinPlotter] category '{key}' has "
                f"fewer than 2 distinct values — skipping violin.",
                UserWarning, stacklevel=2,
            )
            continue

        color = colors.get(key, "#AAAAAA")
        w     = widths[key]

        # Use scipy KDE directly — avoids matplotlib/numpy version
        # incompatibility in ax.violinplot internal GaussianKDE
        from scipy.stats import gaussian_kde
        values = np.asarray(values, dtype=np.float64)
        kde    = gaussian_kde(values, bw_method="scott")
        y_grid = np.linspace(values.min(), values.max(), 200)
        dens   = kde(y_grid)
        max_d  = dens.max()
        scaled = (dens / max_d * w / 2) if max_d > 0 else np.zeros_like(dens)

        ax.fill_betweenx(
            y_grid, i - scaled, i + scaled,
            color=color, alpha=0.75,
        )
        ax.plot(i - scaled, y_grid, color=color, linewidth=0.8, alpha=0.9)
        ax.plot(i + scaled, y_grid, color=color, linewidth=0.8, alpha=0.9)

        if show_box:
            q25, q50, q75 = np.percentile(values, [25, 50, 75])
            bw = w * 0.08
            ax.fill_betweenx(
                [q25, q75], i - bw, i + bw,
                color="white", alpha=0.9, zorder=3,
            )
            ax.scatter([i], [q50], s=20, color="white", zorder=5, linewidths=0)

        if show_points:
            rng    = np.random.default_rng(42)
            jitter = rng.uniform(-w * 0.2, w * 0.2, size=len(values))
            ax.scatter(
                i + jitter, values,
                s=point_size ** 2, color=color,
                alpha=point_alpha, zorder=3, linewidths=0,
            )

        # Per-violin percentile lines
        if pcfg.show and len(values) > 0:
            ls    = _LS_MAP.get(pcfg.linestyle, "--")
            x_l   = i - w / 2
            x_r   = i + w / 2
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
