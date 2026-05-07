"""
occurrence_result_timing_plotter_utils.py
Drawing utilities for OccurrenceResultTimingPlotter.
Imports shared primitives from occurrence_result_plotter_utils.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .occurrence_result_plotter_utils import (
    draw_histogram,
    resolve_x_limits,
)


# ------------------------------------------------------------------ #
# Faceted histogram
# ------------------------------------------------------------------ #

def build_faceted_figure(
    max_n:        int,
    facet_height: float,
    facet_width:  float,
) -> tuple[Figure, list[Axes]]:
    """
    Create a figure with max_n vertically stacked subplots sharing x-axis.

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
    # Always return a list even for max_n=1
    if max_n == 1:
        axes = [axes]
    return fig, list(axes)


def draw_nth_facet(
    ax:         Axes,
    series:     pd.Series,
    nth:        int,
    x_min:      float,
    x_max:      float,
    histogram_cfg,
    font_size:  int,
    n_eligible: int,
    n_total:    int,
    show_denominator_label: bool,
) -> None:
    """
    Draw one nth facet — histogram + labels.

    Parameters
    ----------
    ax : Axes
    series : pd.Series
        time_to_{nth} column, NaN for ineligible entities.
    nth : int
        Which nth occurrence this facet represents.
    x_min, x_max : float
        Shared x-axis limits across all facets.
    histogram_cfg : SimpleHistogramConfig
        Config for this nth (resolved via resolve_histogram_for_nth).
    font_size : int
    n_eligible : int
        Entities with at least nth occurrences.
    n_total : int
        Total cohort size.
    show_denominator_label : bool
        Whether to show "n=X eligible (Y%)" in the subplot title.
    """
    import dataclasses
    # Override x limits with shared scale before drawing
    override = dataclasses.replace(histogram_cfg, x_min=x_min, x_max=x_max)
    draw_histogram(ax=ax, series=series, cfg=override)

    suffix = {1: "st", 2: "nd", 3: "rd"}.get(nth if nth <= 3 else 0, "th")
    label  = histogram_cfg.xlabel or "Days from observation start"
    ax.set_xlabel(label, fontsize=font_size)
    ax.set_ylabel(histogram_cfg.ylabel or "Entities", fontsize=font_size)

    title = f"{nth}{suffix} occurrence"
    if show_denominator_label:
        pct = round(100 * n_eligible / n_total, 1) if n_total else 0.0
        title += f"  —  n={n_eligible:,} eligible ({pct}% of cohort)"
    ax.set_title(title, fontsize=font_size)


# ------------------------------------------------------------------ #
# Survival curve
# ------------------------------------------------------------------ #

def draw_survival_curve(
    ax:           Axes,
    survival_data: pd.DataFrame,
    curve_cfg,
    font_size:    int,
    label:        str | None = None,
) -> None:
    """
    Draw a KM step curve with optional CI band and censoring marks.

    Parameters
    ----------
    ax : Axes
    survival_data : pd.DataFrame
        Columns: day, survival, ci_lower, ci_upper, n_censored.
    curve_cfg : SurvivalCurveConfig
    font_size : int
    label : str | None
        Legend label.
    """
    days     = survival_data["day"].values
    surv     = survival_data["survival"].values
    ci_lower = survival_data["ci_lower"].values
    ci_upper = survival_data["ci_upper"].values

    # Step curve — drawstyle='steps-post' gives the KM staircase shape
    ax.step(
        days, surv,
        where     = "post",
        color     = curve_cfg.color,
        alpha     = curve_cfg.alpha,
        linewidth = 2.0,
        label     = label,
    )

    # CI band
    if curve_cfg.show_ci:
        ax.fill_between(
            days,
            ci_lower,
            ci_upper,
            step  = "post",
            color = curve_cfg.ci_color,
            alpha = curve_cfg.ci_alpha,
        )

    # Censoring tick marks
    if curve_cfg.show_censoring_marks:
        censored_mask = survival_data["n_censored"] > 0
        if censored_mask.any():
            cens_days = survival_data.loc[censored_mask, "day"].values
            cens_surv = survival_data.loc[censored_mask, "survival"].values
            ax.scatter(
                cens_days, cens_surv,
                marker    = "|",
                color     = curve_cfg.censoring_mark_color,
                s         = 60,
                linewidths= 1.5,
                zorder    = 5,
                label     = "Censored" if label else None,
            )

    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Days from observation start", fontsize=font_size)
    ax.set_ylabel("Probability of no first occurrence", fontsize=font_size)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
