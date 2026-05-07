"""
occurrence_result_shape_plotter_utils.py
Drawing utilities for OccurrenceResultShapePlotter.
Imports shared primitives from occurrence_result_plotter_utils.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from .occurrence_result_plotter_utils import draw_histogram


# ------------------------------------------------------------------ #
# Fingerprint scatter
# ------------------------------------------------------------------ #

def draw_fingerprint_scatter(
    ax:          Axes,
    burstiness:  pd.Series,
    memory:      pd.Series,
    scatter_cfg,
    font_size:   int,
    n_eligible:  int,
    n_total:     int,
) -> None:
    """
    Draw burstiness vs memory scatter plot (behavioral fingerprint).

    Only entities with both burstiness and memory defined (n >= 4)
    appear as points. The eligible count is shown in the subtitle.

    Parameters
    ----------
    ax : Axes
    burstiness : pd.Series
        Per-entity burstiness values. NaN for n < 3.
    memory : pd.Series
        Per-entity memory values. NaN for n < 4.
    scatter_cfg : ShapeScatterConfig
    font_size : int
    n_eligible : int
        Entities with both burstiness and memory defined.
    n_total : int
        Total cohort size.
    """
    # Only plot where both are defined
    mask = burstiness.notna() & memory.notna()
    b    = burstiness[mask].values
    m    = memory[mask].values

    if len(b) == 0:
        ax.text(
            0.5, 0.5,
            "Insufficient data\n(requires n ≥ 4 occurrences per entity)",
            transform = ax.transAxes,
            ha        = "center",
            va        = "center",
            fontsize  = font_size,
            color     = "#AAAAAA",
        )
        return

    ax.scatter(
        b, m,
        color     = scatter_cfg.color,
        alpha     = scatter_cfg.alpha,
        s         = scatter_cfg.size,
        linewidths= 0,
        zorder    = 3,
    )

    # Quadrant reference lines
    if scatter_cfg.show_quadrant_lines:
        ax.axvline(
            x         = 0,
            color     = scatter_cfg.quadrant_line_color,
            linestyle = "--",
            linewidth = 1.0,
            zorder    = 2,
        )
        ax.axhline(
            y         = 0,
            color     = scatter_cfg.quadrant_line_color,
            linestyle = "--",
            linewidth = 1.0,
            zorder    = 2,
        )

    if scatter_cfg.show_grid:
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.set_axisbelow(True)

    pct = round(100 * n_eligible / n_total, 1) if n_total else 0.0
    ax.set_xlabel("Burstiness  (< 0 regular  ·  > 0 bursty)", fontsize=font_size)
    ax.set_ylabel("Memory  (< 0 alternating  ·  > 0 persistent)", fontsize=font_size)
    ax.set_title(
        f"n={n_eligible:,} eligible ({pct}% of cohort, requires n ≥ 4)",
        fontsize=font_size - 1,
    )


# ------------------------------------------------------------------ #
# Distribution histograms (center_of_mass, density)
# ------------------------------------------------------------------ #

def draw_distribution_histogram(
    ax:            Axes,
    series:        pd.Series,
    histogram_cfg: "SimpleHistogramConfig",
    font_size:     int,
    n_total:       int,
    auto_xlabel:   str,
    auto_ylabel:   str = "Entities",
) -> None:
    """
    Draw a single distribution histogram with eligible-count subtitle.

    Parameters
    ----------
    ax : Axes
    series : pd.Series
        Values to plot. NaN for ineligible entities — dropped before plotting.
    histogram_cfg : SimpleHistogramConfig
    font_size : int
    n_total : int
        Total cohort size for denominator label.
    auto_xlabel : str
        Fallback x-axis label if histogram_cfg.xlabel is None.
    auto_ylabel : str
        Fallback y-axis label.
    """
    draw_histogram(ax=ax, series=series, cfg=histogram_cfg)

    n_eligible = int(series.notna().sum())
    pct        = round(100 * n_eligible / n_total, 1) if n_total else 0.0

    ax.set_xlabel(histogram_cfg.xlabel or auto_xlabel, fontsize=font_size)
    ax.set_ylabel(histogram_cfg.ylabel or auto_ylabel, fontsize=font_size)
    ax.set_title(
        f"n={n_eligible:,} eligible ({pct}% of cohort)",
        fontsize=font_size - 1,
    )
