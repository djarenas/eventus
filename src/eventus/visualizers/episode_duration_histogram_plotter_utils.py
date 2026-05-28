"""
episode_duration_histogram_plotter_utils.py
Drawing utilities for EpisodeDurationHistogramPlotter.

Shared histogram primitives (compute_bins, draw_histogram,
draw_percentile_lines, resolve_x_limits) live in:
    eventus.visualizers.histogram_utils

This module contains only EpisodeDurationHistogramPlotter-specific
drawing logic — KDE curve, label application, and n-count annotation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from scipy.stats import gaussian_kde

from eventus.visualizers.configs.kde_plot_config import KDEPlotConfig
from eventus.visualizers.configs.base_plot_config import AxisLabels, CanvasConfig


# ── KDE drawing ───────────────────────────────────────────────────────────────

def draw_kde(
    ax:        Axes,
    durations: pd.Series,
    kde_cfg:   KDEPlotConfig,
    canvas:    CanvasConfig,
) -> None:
    """
    Draw a KDE density curve on ax.

    Parameters
    ----------
    ax        : Target Axes.
    durations : Clean duration series — must have at least 2 values.
                Caller is responsible for dropping NaNs first.
    kde_cfg   : KDEPlotConfig — provides style (color, alpha, fill_alpha,
                linewidth, bandwidth, show_grid) and percentile lines.
    canvas    : CanvasConfig — provides font_size.
    """
    from eventus.visualizers.histogram_utils import draw_percentile_lines

    style = kde_cfg.style
    arr   = durations.to_numpy(dtype=np.float64)

    kde    = gaussian_kde(arr, bw_method=style.bandwidth)
    x_min  = max(0.0, float(arr.min()))
    x_max  = float(arr.max())
    x_grid = np.linspace(x_min, x_max, 500)
    y_grid = kde(x_grid)

    # Line
    ax.plot(
        x_grid, y_grid,
        color     = style.color,
        linewidth = style.linewidth,
        alpha     = style.alpha,
        zorder    = 3,
    )

    # Fill under curve
    if style.fill_alpha > 0:
        ax.fill_between(
            x_grid, y_grid,
            alpha  = style.fill_alpha,
            color  = style.color,
            zorder = 2,
        )

    if style.show_grid:
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(bottom=0)

    draw_percentile_lines(ax, durations, kde_cfg.percentiles)


# ── Label application ─────────────────────────────────────────────────────────

def apply_labels(
    ax:        Axes,
    labels:    AxisLabels,
    font_size: int,
    plot_type: str,
    identity:  str | None,
) -> None:
    """
    Apply title, xlabel, and ylabel to an Axes from config labels.

    Falls back to auto-generated values when labels are not set in config.

    Parameters
    ----------
    ax        : Target Axes.
    labels    : AxisLabels from the plot config.
    font_size : Base font size from CanvasConfig.
    plot_type : "histogram" or "kde" — used to choose auto ylabel.
    identity  : Episode identity from EpisodeDurationResult — used in
                auto title. May be None.
    """
    # Title
    title = labels.title
    if title is None:
        suffix = "Distribution" if plot_type == "histogram" else "Density"
        title  = (
            f"Duration {suffix} — {identity}"
            if identity
            else f"Episode Duration {suffix}"
        )
    ax.set_title(title, fontsize=font_size + 1)

    # X label
    xlabel = labels.xlabel or (
        f"Duration ({labels.units})" if labels.units else "Duration (days)"
    )
    ax.set_xlabel(xlabel, fontsize=font_size)

    # Y label
    ylabel = labels.ylabel or (
        "Entities" if plot_type == "histogram" else "Density"
    )
    ax.set_ylabel(ylabel, fontsize=font_size)

    ax.tick_params(labelsize=font_size - 1)

    # Subtitle
    if labels.subtitle:
        ax.text(
            0.98, 0.89,
            labels.subtitle,
            transform = ax.transAxes,
            ha        = "right",
            va        = "top",
            fontsize  = font_size - 1,
            color     = "#555555",
        )


# ── N-count annotation ────────────────────────────────────────────────────────

def annotate_n(
    ax:        Axes,
    n:         int,
    font_size: int,
) -> None:
    """
    Annotate the top-right corner of an Axes with the episode count.

    Parameters
    ----------
    ax        : Target Axes.
    n         : Number of episodes plotted.
    font_size : Base font size from CanvasConfig.
    """
    ax.text(
        0.98, 0.97,
        f"n={n:,} episodes",
        transform = ax.transAxes,
        ha        = "right",
        va        = "top",
        fontsize  = font_size - 1,
        color     = "#555555",
    )
