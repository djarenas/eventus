"""
event_result_volume_plotter_utils.py
Drawing utilities specific to EventResultVolumePlotter.
Shared primitives live in event_result_plotter_utils.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from eventus.visualizers.configs.bar_config import (
    CategoryBarConfig,
    CountDistributionBarConfig,
)


# ── Prevalence computation ────────────────────────────────────────────────────

def compute_prevalence(
    n_col:   pd.Series,
    n_total: int,
) -> dict:
    """
    Compute prevalence counts and percentages from the n column.

    Parameters
    ----------
    n_col   : Per-entity event count column.
    n_total : Total cohort size.

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


def compute_count_distribution(
    n_col:   pd.Series,
    n_total: int,
    max_n:   int,
) -> list[dict]:
    """
    Bucket per-entity counts into discrete bars with an overflow bucket.

    Produces one entry per bucket from n=0 up to n=max_n-1, then a final
    overflow bucket for n >= max_n.

    Parameters
    ----------
    n_col   : Per-entity event count column.
    n_total : Total cohort size.
    max_n   : Overflow cutoff — entities with n >= max_n go into the last bucket.

    Returns
    -------
    list of dicts, each with keys:
        label   : Display label, e.g. "n=0", "n=1", "n=5+"
        count   : Raw entity count in this bucket.
        pct     : Percentage of cohort in this bucket.
    """
    buckets = []
    for i in range(max_n):
        count = int((n_col == i).sum())
        buckets.append({
            "label": f"n={i}",
            "count": count,
            "pct":   round(100 * count / n_total, 1) if n_total else 0.0,
        })
    # Overflow bucket
    overflow_count = int((n_col >= max_n).sum())
    buckets.append({
        "label": f"n={max_n}+",
        "count": overflow_count,
        "pct":   round(100 * overflow_count / n_total, 1) if n_total else 0.0,
    })
    return buckets


# ── Wilson CI ─────────────────────────────────────────────────────────────────

def _wilson_ci(n: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score confidence interval for a proportion.
    Behaves well near 0 and 1 unlike the normal approximation.

    Returns
    -------
    tuple[float, float]
        (lower, upper) as percentages in [0, 100].
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


# ── Prevalence bar drawing ────────────────────────────────────────────────────

def draw_prevalence_bar(
    ax:         Axes,
    prevalence: dict,
    bar_cfg:    CategoryBarConfig,
    font_size:  int,
    identity:   str,
) -> None:
    """
    Draw a bar chart of % with any / % with multiple / % with none.

    Parameters
    ----------
    ax         : Target Axes.
    prevalence : Output of compute_prevalence().
    bar_cfg    : CategoryBarConfig — colors, alpha, CI and label settings.
    font_size  : Base font size for axis labels and annotations.
    identity   : Used for the x-axis label.
    """
    n_total    = prevalence["n_any"] + prevalence["n_none"]
    categories = ["Any event", "Multiple events", "No event"]
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

    if bar_cfg.show_ci:
        for i, (bar, n) in enumerate(zip(bars, counts)):
            lo, hi = _wilson_ci(n, n_total)
            mid    = pcts[i]
            ax.errorbar(
                x         = bar.get_x() + bar.get_width() / 2,
                y         = mid,
                yerr      = [[mid - lo], [hi - mid]],
                fmt       = "none",
                color     = bar_cfg.ci_color,
                alpha     = bar_cfg.ci_alpha,
                capsize   = 4,
                linewidth = 1.5,
                zorder    = 5,
            )

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
    ax.set_xlabel(identity,      fontsize=font_size)
    ax.set_ylim(0, 110)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)


# ── Discrete percentile lines ─────────────────────────────────────────────────

def draw_discrete_percentile_lines(
    ax:      Axes,
    n_col:   pd.Series,
    bar_cfg: CountDistributionBarConfig,
    bars:    list,
    labels:  list[str],
) -> None:
    """
    Draw vertical percentile reference lines snapped to bar centres.

    Because the x-axis is categorical, lines are positioned at the x centre
    of the bar whose label matches the rounded percentile value from the raw
    n column. Values >= max_n snap to the overflow bar.

    Parameters
    ----------
    ax      : Target Axes.
    n_col   : Raw per-entity event count column (before bucketing).
    bar_cfg : CountDistributionBarConfig — provides percentile_lines config.
    bars    : List of Bar patches returned by ax.bar().
    labels  : List of bar labels in plot order, e.g. ["n=0", "n=1", ..., "n=5+"]
    """
    pct_cfg = bar_cfg.percentile_lines
    if not pct_cfg.show:
        return

    clean = n_col.dropna().to_numpy()
    if clean.size == 0:
        return

    # Build label → bar centre lookup
    bar_centres = {
        label: bar.get_x() + bar.get_width() / 2
        for label, bar in zip(labels, bars)
    }
    overflow_label = labels[-1]  # e.g. "n=5+"

    for p in pct_cfg.values:
        value    = float(np.percentile(clean, p))
        snapped  = int(round(value))
        label    = f"n={snapped}" if snapped < bar_cfg.max_n else overflow_label
        x_centre = bar_centres.get(label)

        if x_centre is None:
            continue

        ax.axvline(
            x_centre,
            linestyle = pct_cfg.linestyle,
            color     = pct_cfg.color,
            linewidth = 1.2,
            alpha     = 0.9,
        )
        if pct_cfg.show_labels:
            ax.text(
                x_centre,
                ax.get_ylim()[1],
                f"P{p}",
                rotation = 90,
                va       = "top",
                ha       = "right",
                fontsize = 8,
            )


# ── Count distribution bar drawing ───────────────────────────────────────────

def draw_count_distribution_bar(
    ax:        Axes,
    buckets:   list[dict],
    n_col:     pd.Series,
    n_total:   int,
    bar_cfg:   CountDistributionBarConfig,
    font_size: int,
    identity:  str,
) -> None:
    """
    Draw a discrete count distribution bar chart.

    Parameters
    ----------
    ax        : Target Axes.
    buckets   : Output of compute_count_distribution().
    n_col     : Raw per-entity event count column — used for percentile lines.
    n_total   : Total cohort size — used for CI computation.
    bar_cfg   : CountDistributionBarConfig — color, overflow cutoff, display options.
    font_size : Base font size for axis labels and annotations.
    identity  : Used for the x-axis label.
    """
    labels = [b["label"] for b in buckets]
    counts = [b["count"] for b in buckets]
    pcts   = [b["pct"]   for b in buckets]
    values = pcts if bar_cfg.show_as_pct else counts

    bars = ax.bar(
        labels,
        values,
        color = bar_cfg.color,
        alpha = bar_cfg.alpha,
        width = 0.7,
    )

    if bar_cfg.show_ci and bar_cfg.show_as_pct:
        for bar, n, pct in zip(bars, counts, pcts):
            lo, hi = _wilson_ci(n, n_total)
            lower_err = max(pct - lo, 0)  
            upper_err = min(max(hi - pct, 0), 100)  
            ax.errorbar(
                x         = bar.get_x() + bar.get_width() / 2,
                y         = pct,
                yerr      = [[lower_err], [upper_err]]  ,
                fmt       = "none",
                color     = bar_cfg.ci_color,
                alpha     = bar_cfg.ci_alpha,
                capsize   = 4,
                linewidth = 1.5,
                zorder    = 5,
            )

    if bar_cfg.show_count_labels:
        for bar, pct, n in zip(bars, pcts, counts):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + (0.5 if bar_cfg.show_as_pct else max(counts) * 0.01),
                f"{pct}%\n(n={n:,})",
                ha       = "center",
                va       = "bottom",
                fontsize = font_size - 1,
            )

    draw_discrete_percentile_lines(
        ax      = ax,
        n_col   = n_col,
        bar_cfg = bar_cfg,
        bars    = list(bars),
        labels  = labels,
    )

    ylabel = "% of cohort" if bar_cfg.show_as_pct else "Number of entities"
    ax.set_ylabel(ylabel,   fontsize=font_size)
    ax.set_xlabel(identity, fontsize=font_size)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
