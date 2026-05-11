"""
occurrence_result_shape_plotter_utils.py
Drawing utilities for OccurrenceResultShapePlotter.
Shared primitives live in occurrence_result_plotter_utils.
"""
from __future__ import annotations

import pandas as pd
from matplotlib.axes import Axes

from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.configs.occurrence_result_shape_config import ShapeScatterConfig
from eventus.visualizers.occurrences.occurrence_result_plotter_utils import (
    draw_histogram,
    draw_percentile_lines,
)


# ── Fingerprint scatter ───────────────────────────────────────────────────────

def draw_fingerprint_scatter(
    ax:         Axes,
    burstiness: pd.Series,
    memory:     pd.Series,
    scatter_cfg: ShapeScatterConfig,
    font_size:  int,
    n_eligible: int,
    n_total:    int,
) -> None:
    """
    Draw burstiness vs memory scatter plot (behavioral fingerprint).

    Only entities with both burstiness and memory defined (n >= 4)
    appear as points.

    Parameters
    ----------
    ax          : Target Axes.
    burstiness  : Per-entity burstiness values. NaN for n < 3.
    memory      : Per-entity memory values. NaN for n < 4.
    scatter_cfg : ShapeScatterConfig.
    font_size   : Base font size.
    n_eligible  : Entities with both burstiness and memory defined.
    n_total     : Total cohort size.
    """
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
        color      = scatter_cfg.color,
        alpha      = scatter_cfg.alpha,
        s          = scatter_cfg.size,
        linewidths = 0,
        zorder     = 3,
    )

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

    xlabel = scatter_cfg.labels.xlabel or "Burstiness  (< 0 regular  ·  > 0 bursty)"
    ylabel = scatter_cfg.labels.ylabel or "Memory  (< 0 alternating  ·  > 0 persistent)"
    ax.set_xlabel(xlabel, fontsize=font_size)
    ax.set_ylabel(ylabel, fontsize=font_size)

    pct = round(100 * n_eligible / n_total, 1) if n_total else 0.0
    ax.set_title(
        f"n={n_eligible:,} eligible ({pct}% of cohort, requires n ≥ 4)",
        fontsize=font_size - 1,
    )


# ── Distribution histograms ───────────────────────────────────────────────────

def draw_distribution_histogram(
    ax:            Axes,
    series:        pd.Series,
    histogram_cfg: HistogramPlotConfig,
    font_size:     int,
    n_total:       int,
) -> None:
    """
    Draw a single distribution histogram with eligible-count subtitle.

    Labels are read directly from histogram_cfg.labels — set sensible
    defaults via the factory functions in occurrence_result_shape_config.

    Parameters
    ----------
    ax            : Target Axes.
    series        : Values to plot. NaN for ineligible entities — dropped before plotting.
    histogram_cfg : HistogramPlotConfig — provides bins, style, labels, percentile_lines.
    font_size     : Base font size.
    n_total       : Total cohort size for denominator label.
    """
    draw_histogram(ax=ax, series=series, cfg=histogram_cfg)
    draw_percentile_lines(ax=ax, series=series, pct_cfg=histogram_cfg.percentile_lines)

    n_eligible = int(series.notna().sum())
    pct        = round(100 * n_eligible / n_total, 1) if n_total else 0.0

    ax.set_xlabel(histogram_cfg.labels.xlabel, fontsize=font_size)
    ax.set_ylabel(histogram_cfg.labels.ylabel, fontsize=font_size)
    ax.set_title(
        f"n={n_eligible:,} eligible ({pct}% of cohort)",
        fontsize=font_size - 1,
    )
