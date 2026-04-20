"""
events_duration_violin_plotter_utils.py
Pure utility functions for EventsDurationViolinPlotter.
No class state — only data and config inputs.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd

_WARN_PREFIX = "[EventsDurationViolinPlotter]"
_LS_MAP      = {"dashed": "--", "dotted": ":", "solid": "-"}


# ── Data preparation ──────────────────────────────────────────────────────

def prepare_data(
    data:         pd.DataFrame,
    entity_col:   str,
    duration_col: str,
    stratify_by:  str,
    config,
) -> tuple[list[str], dict[str, np.ndarray]]:
    """
    Validate categories and build {key: durations_array} mapping.

    Categories in config but not in data → raise.
    Categories in data but not in config → warn, ignore.
    Reserved key 'all_data' in stratify_by column values → raise.
    """
    if "all_data" in data[stratify_by].astype(str).values:
        raise ValueError(
            f"{_WARN_PREFIX} Error: 'all_data' is a reserved key and cannot "
            f"appear as a value in the '{stratify_by}' column. "
            f"Rename that category in your data before plotting."
        )

    data_cats   = set(data[stratify_by].dropna().unique())
    config_cats = set(config.category_keys_non_total)

    missing_in_data = config_cats - data_cats
    if missing_in_data:
        raise ValueError(
            f"{_WARN_PREFIX} Error: categories configured in stratify but "
            f"not found in '{stratify_by}' column: "
            f"{sorted(missing_in_data)}. "
            f"Check your data or remove these from the config."
        )

    ignored = data_cats - config_cats
    if ignored:
        warnings.warn(
            f"{_WARN_PREFIX} categories found in '{stratify_by}' but not "
            f"in config — ignoring: {sorted(ignored)}. "
            f"Add them to the stratify section to include them.",
            UserWarning, stacklevel=4,
        )

    arrays = {}
    if config.has_total:
        arrays["all_data"] = data[duration_col].dropna().values
    for key in config.category_keys_non_total:
        mask        = data[stratify_by] == key
        arrays[key] = data.loc[mask, duration_col].dropna().values

    plot_order = (
        ["all_data"] if config.has_total else []
    ) + config.category_keys_non_total

    return plot_order, arrays


# ── Width scaling ─────────────────────────────────────────────────────────

def compute_widths(
    arrays:     dict[str, np.ndarray],
    plot_order: list[str],
    max_width:  float = 0.8,
) -> dict[str, float]:
    """
    Scale violin widths linearly with n — area-proportional.
    A category with half the data gets half the width.
    """
    ns    = {k: len(arrays[k]) for k in plot_order}
    max_n = max(ns.values()) if ns else 1
    return {k: max_width * (ns[k] / max_n) for k in plot_order}


# ── Violin drawing ────────────────────────────────────────────────────────

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
    Draw all violins using matplotlib's ax.violinplot — one call per
    violin so each can have its own width and color.
    Percentile lines are drawn per-violin from each violin's own data.
    """
    for i, key in enumerate(plot_order):
        values = arrays[key]
        if len(values) == 0:
            continue
        # Need at least 2 distinct values for KDE — skip and warn
        if len(np.unique(values)) < 2:
            import warnings
            warnings.warn(
                f"{_WARN_PREFIX} category '{key}' has fewer than 2 distinct "
                f"values ({len(values)} total) — skipping violin.",
                UserWarning, stacklevel=2,
            )
            continue

        color = colors.get(key, "#AAAAAA")
        w     = widths[key]

        parts = ax.violinplot(
            [values],       # must be list-wrapped — sanitize_sequence strips bare arrays
            positions   = [i],
            widths      = [w],
            showmedians = show_box,
            showextrema = show_box,
            showmeans   = False,
        )

        # Style body
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.75)
            pc.set_linewidth(0.8)

        # Style median and extrema lines
        if show_box:
            for part in ["cmedians", "cmins", "cmaxes", "cbars"]:
                if part in parts:
                    parts[part].set_color("#333333")
                    parts[part].set_linewidth(1.0)

        # Jittered data points
        if show_points:
            rng    = np.random.default_rng(42)
            jitter = rng.uniform(-w * 0.2, w * 0.2, size=len(values))
            ax.scatter(
                i + jitter,
                values,
                s          = point_size ** 2,
                color      = color,
                alpha      = point_alpha,
                zorder     = 3,
                linewidths = 0,
            )

        # Per-violin percentile lines
        draw_percentile_lines(ax, x_pos=i, width=w, values=values, pcfg=pcfg)


# ── Percentile lines ──────────────────────────────────────────────────────

def draw_percentile_lines(
    ax,
    x_pos:   float,
    width:   float,
    values:  np.ndarray,
    pcfg,
) -> None:
    """
    Draw per-violin percentile lines — horizontal segments spanning
    only the width of that violin, computed from that violin's own data.

    Parameters
    ----------
    ax : matplotlib Axes
    x_pos : float
        X center position of this violin.
    width : float
        Full width of this violin — lines span x_pos ± width/2.
    values : np.ndarray
        Duration values for this violin only.
    pcfg : PercentilesConfig
    """
    if not pcfg.show or len(values) == 0:
        return

    ls    = _LS_MAP.get(pcfg.linestyle, "--")
    x_l   = x_pos - width / 2
    x_r   = x_pos + width / 2

    for p in pcfg.values:
        val = float(np.percentile(values, p))
        ax.hlines(
            val,
            xmin      = x_l,
            xmax      = x_r,
            colors    = pcfg.color,
            linewidth = 1.2,
            linestyle = ls,
            zorder    = 4,
        )
        if pcfg.show_labels:
            ax.text(
                x_r + 0.02,
                val,
                f"p{p}={val:.1f}",
                fontsize = 7,
                color    = pcfg.color,
                va       = "center",
                ha       = "left",
            )
