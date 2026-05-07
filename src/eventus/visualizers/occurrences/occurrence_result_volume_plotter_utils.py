"""
occurrence_result_volume_plotter_utils.py
Drawing utilities for OccurrenceResultVolumePlotter.
Imports shared primitives from occurrence_result_plotter_utils.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes


# ------------------------------------------------------------------ #
# Prevalence bar
# ------------------------------------------------------------------ #

def compute_prevalence(
    n_col:    pd.Series,
    n_total:  int,
) -> dict:
    """
    Compute prevalence counts and percentages from the n column.

    Parameters
    ----------
    n_col : pd.Series
        Per-entity occurrence count column.
    n_total : int
        Total cohort size.

    Returns
    -------
    dict with keys:
        n_any, n_multiple, n_none,
        pct_any, pct_multiple, pct_none
    """
    n_any      = int((n_col > 0).sum())
    n_multiple = int((n_col > 1).sum())
    n_none     = n_total - n_any
    return {
        "n_any":        n_any,
        "n_multiple":   n_multiple,
        "n_none":       n_none,
        "pct_any":      round(100 * n_any      / n_total, 1) if n_total else 0.0,
        "pct_multiple": round(100 * n_multiple / n_total, 1) if n_total else 0.0,
        "pct_none":     round(100 * n_none     / n_total, 1) if n_total else 0.0,
    }


def _wilson_ci(n: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score confidence interval for a proportion.
    Behaves well near 0 and 1 unlike normal approximation.

    Returns
    -------
    tuple[float, float]
        (lower, upper) as percentages [0, 100].
    """
    if total == 0:
        return 0.0, 0.0
    p      = n / total
    denom  = 1 + z ** 2 / total
    center = (p + z ** 2 / (2 * total)) / denom
    spread = z * np.sqrt(p * (1 - p) / total + z ** 2 / (4 * total ** 2)) / denom
    lower  = max(0.0, (center - spread) * 100)
    upper  = min(100.0, (center + spread) * 100)
    return lower, upper


def draw_prevalence_bar(
    ax:         Axes,
    prevalence: dict,
    bar_cfg,
    font_size:  int,
    identity:   str,
) -> None:
    """
    Draw a horizontal bar chart of % with any / % with multiple / % with none.

    Parameters
    ----------
    ax : Axes
    prevalence : dict
        Output of compute_prevalence().
    bar_cfg : VolumeBarConfig
    font_size : int
    identity : str
        Used for x-axis label.
    """
    n_total    = prevalence["n_any"] + prevalence["n_none"]
    categories = ["Any occurrence", "Multiple occurrences", "No occurrence"]
    counts     = [prevalence["n_any"], prevalence["n_multiple"], prevalence["n_none"]]
    pcts       = [prevalence["pct_any"], prevalence["pct_multiple"], prevalence["pct_none"]]
    colors     = [bar_cfg.color_any, bar_cfg.color_multiple, bar_cfg.color_none]

    bars = ax.bar(
        categories,
        pcts,
        color = colors,
        alpha = bar_cfg.alpha,
        width = 0.5,
    )

    # CI error bars
    if bar_cfg.show_ci:
        for i, (bar, n) in enumerate(zip(bars, counts)):
            lo, hi = _wilson_ci(n, n_total)
            mid    = pcts[i]
            ax.errorbar(
                x        = bar.get_x() + bar.get_width() / 2,
                y        = mid,
                yerr     = [[mid - lo], [hi - mid]],
                fmt      = "none",
                color    = bar_cfg.ci_color,
                alpha    = bar_cfg.ci_alpha,
                capsize  = 4,
                linewidth= 1.5,
                zorder   = 5,
            )

    # Percentage annotations
    if bar_cfg.show_pct_labels:
        for bar, pct, n in zip(bars, pcts, counts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{pct}%\n(n={n:,})",
                ha       = "center",
                va       = "bottom",
                fontsize = font_size - 1,
            )

    ax.set_ylabel("% of cohort", fontsize=font_size)
    ax.set_xlabel(identity, fontsize=font_size)
    ax.set_ylim(0, 110)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
