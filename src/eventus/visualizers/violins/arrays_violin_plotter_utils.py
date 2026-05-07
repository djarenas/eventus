"""
arrays_violin_plotter_utils.py
Pure drawing utilities for ArraysViolinPlotter.

No validation, no I/O — only clean arrays and matplotlib axes in,
rendered plot elements out.

Functions
---------
compute_widths          — sqrt(n)-scaled violin widths
draw_violin_body        — single violin shape
draw_box                — IQR box + median dot overlay
draw_points             — jittered scatter overlay
draw_percentile_lines   — horizontal reference lines at chosen percentiles
apply_y_bounds          — set ax y limits from ViolinAxisConfig
build_tick_labels       — "Label\n(n=N)" strings for x ticks
"""
from __future__ import annotations

import warnings
import numpy as np
import matplotlib.axes
from scipy.stats import gaussian_kde

_WARN_PREFIX = "[ArraysViolinPlotter]"
_RNG         = np.random.default_rng(42)   # seeded for reproducible jitter
_LS_MAP      = {"dashed": "--", "dotted": ":", "solid": "-"}


# ── Width scaling ─────────────────────────────────────────────────────────────

def compute_widths(
    arrays:     dict[str, np.ndarray],
    plot_order: list[str],
    max_width:  float = 0.8,
) -> dict[str, float]:
    """
    Scale violin widths by sqrt(n) relative to the largest category.

    Parameters
    ----------
    arrays     : cleaned {key: 1-D array} dict
    plot_order : keys in display order
    max_width  : width assigned to the largest category (default 0.8)

    Returns
    -------
    dict[str, float] — width per key
    """
    sizes = {k: len(arrays[k]) for k in plot_order}
    max_n = max(sizes.values())
    return {
        k: max_width * (sizes[k] / max_n) ** 0.5
        for k in plot_order
    }


# ── Single violin components ──────────────────────────────────────────────────

def draw_violin_body(
    ax:        matplotlib.axes.Axes,
    arr:       np.ndarray,
    position:  int,
    width:     float,
    color:     str,
    bandwidth: str,
) -> None:
    """
    Draw a KDE outline-only violin at the given x position.

    Uses gaussian_kde for a clean outline rather than matplotlib's
    default filled violinplot. Draws left and right outlines as lines,
    plus median, range whisker, and whisker caps.

    Falls back to a single summary hline if fewer than 2 unique values.
    """
    if len(np.unique(arr)) < 2:
        warnings.warn(
            f"{_WARN_PREFIX} an array has fewer than 2 unique values — "
            f"drawing a summary line only.",
            UserWarning, stacklevel=3,
        )
        y = float(np.median(arr))
        ax.hlines(y, position - width / 2, position + width / 2,
                  colors="#333333", linewidth=1.4, zorder=4)
        return

    kde    = gaussian_kde(arr, bw_method=bandwidth)
    y_grid = np.linspace(arr.min(), arr.max(), 200)
    dens   = kde(y_grid)
    max_d  = dens.max()
    scaled = (dens / max_d * width / 2) if max_d > 0 else np.zeros_like(dens)

    ax.plot(position - scaled, y_grid, color=color, linewidth=1.4, alpha=0.95, zorder=3)
    ax.plot(position + scaled, y_grid, color=color, linewidth=1.4, alpha=0.95, zorder=3)


def draw_box(
    ax:       matplotlib.axes.Axes,
    arr:      np.ndarray,
    position: int,
    color:    str,
) -> None:
    """
    Draw violin summary lines: median, full range whisker, whisker caps.

    Median  — thick horizontal line in the violin color
    Range   — thin vertical line from min to max
    Caps    — short horizontal lines at min and max
    """
    if len(np.unique(arr)) < 2:
        return   # degenerate case already handled by draw_violin_body

    width  = 0.8   # cap width — cosmetic, independent of violin width
    q50    = float(np.percentile(arr, 50))
    vmin   = float(arr.min())
    vmax   = float(arr.max())

    # range whisker
    ax.vlines(position, vmin, vmax, colors="#666666", linewidth=0.9, alpha=0.7, zorder=3)
    # whisker caps
    ax.hlines([vmin, vmax],
              position - width * 0.18, position + width * 0.18,
              colors="#666666", linewidth=1.0, zorder=4)
    # median line
    ax.hlines(q50,
              position - width / 2, position + width / 2,
              colors="#333333", linewidth=1.4, zorder=5)


def draw_points(
    ax:       matplotlib.axes.Axes,
    arr:      np.ndarray,
    position: int,
    width:    float,
    color:    str,
    alpha:    float,
    size:     float,
) -> None:
    """Draw seeded jittered scatter points over a violin."""
    jitter = _RNG.uniform(-width * 0.2, width * 0.2, size=len(arr))
    ax.scatter(
        position + jitter, arr,
        alpha     = alpha,
        s         = size ** 2,
        color     = color,
        zorder    = 2,
        linewidths= 0,
    )


def draw_percentile_lines(
    ax:        matplotlib.axes.Axes,
    arr:       np.ndarray,
    position:  int,
    width:     float,
    pcfg,
    font_size: int,
) -> None:
    """
    Draw horizontal reference lines at configured percentile values.

    Parameters
    ----------
    pcfg : PercentilesConfig
    """
    ls = _LS_MAP.get(pcfg.linestyle, "--")
    for pval in pcfg.values:
        y = np.percentile(arr, pval)
        ax.hlines(
            y,
            position - width / 2,
            position + width / 2,
            colors     = pcfg.color,
            linestyles = ls,
            linewidth  = 1.2,
            zorder     = 5,
        )
        if pcfg.show_labels:
            ax.text(
                position + width / 2 + 0.02, y,
                f"p{pval}={y:.1f}",
                fontsize = font_size - 3,
                va       = "center",
                ha       = "left",
                color    = pcfg.color,
            )


# ── Axis helpers ──────────────────────────────────────────────────────────────

def apply_y_bounds(ax: matplotlib.axes.Axes, axcfg) -> None:
    """
    Apply y_min / y_max from a ViolinAxisConfig if set.

    Parameters
    ----------
    axcfg : ViolinAxisConfig
    """
    if axcfg.y_min is not None or axcfg.y_max is not None:
        ax.set_ylim(bottom=axcfg.y_min, top=axcfg.y_max)


def build_tick_labels(
    plot_order: list[str],
    resolved:   dict,
    sizes:      dict[str, int],
) -> list[str]:
    """
    Build x-tick label strings: "Display Label\\n(n=N,NNN)".
    Falls back to the raw key if no label is configured.

    Parameters
    ----------
    resolved : dict[str, CategoryConfig]
    sizes    : dict[str, int] — number of elements per key
    """
    labels = []
    for key in plot_order:
        cat   = resolved[key]
        label = cat.label if cat.label else key
        n     = sizes[key]
        labels.append(f"{label}\n(n={n:,})")
    return labels
