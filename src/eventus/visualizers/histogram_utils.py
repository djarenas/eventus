"""
histogram_utils.py
Histogram and distribution drawing utilities shared across all
eventus visualizers that draw histograms or distribution plots.

Functions
---------
compute_bins            — derive bin edges from BinsConfig and data
draw_histogram          — draw a histogram on an Axes
draw_percentile_lines   — draw vertical percentile reference lines
resolve_x_limits        — compute shared x limits across multiple series
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from eventus.visualizers.configs.bins_config import (
    AutoSpec,
    BinsConfig,
    CustomSpec,
    LogSpec,
    UniformSpec,
)
from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.configs.percentiles_config import PercentilesConfig


# ── Bin computation ───────────────────────────────────────────────────────────

def compute_bins(series: pd.Series, bins_cfg: BinsConfig) -> np.ndarray:
    """
    Derive bin edges from a BinsConfig and a data series.

    Parameters
    ----------
    series   : The data series to bin. NaNs are dropped before computing.
    bins_cfg : BinsConfig describing the bin strategy.

    Returns
    -------
    np.ndarray of bin edges.
    """
    clean = series.dropna().to_numpy()
    if clean.size == 0:
        return np.array([0.0, 1.0])

    spec = bins_cfg.spec

    if isinstance(spec, AutoSpec):
        return np.histogram_bin_edges(clean, bins="auto")

    if isinstance(spec, CustomSpec):
        return np.asarray(spec.edges, dtype=float)

    if isinstance(spec, UniformSpec):
        left  = float(spec.min) if spec.min is not None else float(np.min(clean))
        right = float(spec.max) if spec.max is not None else float(np.max(clean))
        if right <= left:
            right = left + 1.0
        return np.linspace(left, right, spec.n_bins + 1)

    if isinstance(spec, LogSpec):
        if spec.min is not None:
            left = float(spec.min)
        else:
            positive = clean[clean > 0]
            if positive.size == 0:
                raise ValueError(
                    "[histogram_utils] Cannot use log bins: "
                    "data has no positive values."
                )
            left = float(np.min(positive))

        if spec.max is not None:
            right = float(spec.max)
        else:
            positive = clean[clean > 0]
            if positive.size == 0:
                raise ValueError(
                    "[histogram_utils] Cannot use log bins: "
                    "data has no positive values."
                )
            right = float(np.max(positive))

        if right <= left:
            right = left * 10.0

        return np.logspace(np.log10(left), np.log10(right), spec.n_bins + 1)

    raise TypeError(
        f"[histogram_utils] Unsupported bins spec: {type(spec).__name__}"
    )


# ── Histogram drawing ─────────────────────────────────────────────────────────

def draw_histogram(
    ax:     Axes,
    series: pd.Series,
    cfg:    HistogramPlotConfig,
    label:  str | None = None,
) -> None:
    """
    Draw a histogram on ax using the bins and style from cfg.

    Parameters
    ----------
    ax     : Target Axes.
    series : Data series. NaNs are dropped.
    cfg    : HistogramPlotConfig — provides bins and style.
    label  : Optional legend label (used in stratified plots).
    """
    clean = series.dropna()
    if clean.empty:
        ax.text(
            0.5, 0.5, "No data",
            transform = ax.transAxes,
            ha        = "center",
            va        = "center",
            fontsize  = 10,
            color     = "#AAAAAA",
        )
        return

    bins  = compute_bins(clean, cfg.bins)
    style = cfg.style

    ax.hist(
        clean.to_numpy(),
        bins      = bins,
        color     = style.color,
        edgecolor = style.edgecolor,
        alpha     = style.alpha,
        label     = label,
    )
    ax.set_xlim(float(bins[0]), float(bins[-1]))

    if style.show_grid:
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)


# ── Percentile lines ──────────────────────────────────────────────────────────

def draw_percentile_lines(
    ax:      Axes,
    series:  pd.Series,
    pct_cfg: PercentilesConfig,
) -> None:
    """
    Draw vertical percentile reference lines on ax.

    Parameters
    ----------
    ax      : Target Axes.
    series  : Data series. NaNs are dropped.
    pct_cfg : PercentilesConfig.
    """
    if not pct_cfg.show:
        return

    clean = series.dropna().to_numpy()
    if clean.size == 0:
        return

    for p in pct_cfg.values:
        x = float(np.percentile(clean, p))
        ax.axvline(
            x,
            linestyle = pct_cfg.linestyle,
            color     = pct_cfg.color,
            linewidth = 1.2,
            alpha     = 0.9,
        )
        if pct_cfg.show_labels:
            ax.text(
                x, ax.get_ylim()[1],
                f"P{p}",
                rotation = 90,
                va       = "top",
                ha       = "right",
                fontsize = 8,
            )


# ── Shared x-limits ───────────────────────────────────────────────────────────

def resolve_x_limits(
    series_list: list[pd.Series],
    bins_cfg:    BinsConfig,
) -> tuple[float, float]:
    """
    Compute shared x-axis limits across multiple series for faceted plots.

    Respects explicit min/max from the bins config where set;
    falls back to the data range otherwise.

    Parameters
    ----------
    series_list : List of data series (one per facet).
    bins_cfg    : BinsConfig — explicit bounds take priority.

    Returns
    -------
    tuple[float, float] — (x_min, x_max)
    """
    spec = bins_cfg.spec

    if isinstance(spec, CustomSpec):
        return float(spec.edges[0]), float(spec.edges[-1])

    if isinstance(spec, (UniformSpec, LogSpec)) and \
       spec.min is not None and spec.max is not None:
        return float(spec.min), float(spec.max)

    all_vals = (
        pd.concat([s.dropna() for s in series_list])
        if series_list
        else pd.Series(dtype=float)
    )
    if all_vals.empty:
        return 0.0, 1.0

    data_min = float(all_vals.min())
    data_max = float(all_vals.max())

    if isinstance(spec, UniformSpec):
        x_min = float(spec.min) if spec.min is not None else data_min
        x_max = float(spec.max) if spec.max is not None else data_max
    elif isinstance(spec, LogSpec):
        pos = all_vals[all_vals > 0]
        if pos.empty:
            return 0.0, 1.0
        x_min = float(spec.min) if spec.min is not None else float(pos.min())
        x_max = float(spec.max) if spec.max is not None else float(pos.max())
    else:
        x_min, x_max = data_min, data_max

    if x_max <= x_min:
        x_max = x_min + 1.0
    return x_min, x_max
