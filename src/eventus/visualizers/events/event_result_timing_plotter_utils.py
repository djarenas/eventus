"""
event_result_timing_plotter_utils.py
Drawing utilities for EventResultTimingPlotter.
Shared primitives live in event_result_plotter_utils.
"""
from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.events.event_result_plotter_utils import (
    draw_histogram,
    draw_percentile_lines,
)


# ── Faceted histogram ─────────────────────────────────────────────────────────

def build_faceted_figure(
    max_n:        int,
    facet_height: float,
    facet_width:  float,
) -> tuple[Figure, list[Axes]]:
    """
    Create a figure with max_n vertically stacked subplots sharing the x-axis.

    Parameters
    ----------
    max_n        : Number of subplots (one per nth event).
    facet_height : Height in inches of each subplot row.
    facet_width  : Width in inches of the figure.

    Returns
    -------
    tuple[Figure, list[Axes]]
    """
    fig, axes = plt.subplots(
        nrows   = max_n,
        ncols   = 1,
        figsize = (facet_width, facet_height * max_n),
        sharex  = True,
    )
    if max_n == 1:
        axes = [axes]
    return fig, list(axes)


def draw_nth_facet(
    ax:                     Axes,
    series:                 pd.Series,
    nth:                    int,
    x_min:                  float,
    x_max:                  float,
    histogram_cfg:          HistogramPlotConfig,
    font_size:              int,
    n_eligible:             int,
    n_total:                int,
    show_denominator_label: bool = True,
) -> None:
    """
    Draw one nth facet — histogram, percentile lines, and axis labels.

    Shared x-axis limits are applied directly to the axes after drawing
    so all facets use the same scale regardless of per-nth bin settings.

    Parameters
    ----------
    ax                     : Target Axes.
    series                 : time_to_{nth} column. NaN for ineligible entities.
    nth                    : Which nth event this facet represents.
    x_min, x_max           : Shared x-axis limits across all facets.
    histogram_cfg          : HistogramPlotConfig resolved for this nth.
    font_size              : Base font size.
    n_eligible             : Entities with at least nth events.
    n_total                : Total cohort size.
    show_denominator_label : Show 'n=X eligible (Y%)' in the subplot title.
    """
    draw_histogram(ax=ax, series=series, cfg=histogram_cfg)
    draw_percentile_lines(ax=ax, series=series, pct_cfg=histogram_cfg.percentile_lines)

    # Apply shared x scale after drawing — never mutate the config
    ax.set_xlim(x_min, x_max)

    xlabel = histogram_cfg.labels.xlabel or "Days from observation start"
    ylabel = histogram_cfg.labels.ylabel or "Entities"
    ax.set_xlabel(xlabel, fontsize=font_size)
    ax.set_ylabel(ylabel, fontsize=font_size)

    suffix = {1: "st", 2: "nd", 3: "rd"}.get(nth if nth <= 3 else 0, "th")
    title  = f"{nth}{suffix} event"
    if show_denominator_label:
        pct = round(100 * n_eligible / n_total, 1) if n_total else 0.0
        title += f"  —  n={n_eligible:,} eligible ({pct}% of cohort)"
    ax.set_title(title, fontsize=font_size)
