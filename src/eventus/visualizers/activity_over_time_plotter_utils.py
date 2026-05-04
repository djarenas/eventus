"""
activity_over_time_plotter_utils.py
Pure utility functions for ActivityOverTimePlotter.
No class state — only data and config inputs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# ── X-axis formatting ─────────────────────────────────────────────────────

def build_xticks(
    max_days: int,
    x_unit:   str,
    interval: int,
) -> tuple[list[int], list[str]]:
    """
    Build tick positions (day offsets) and labels.

    Parameters
    ----------
    max_days : int
        Maximum day offset in the timeseries.
    x_unit : str
        "days", "months", or "years".
    interval : int
        Tick every N units.

    Returns
    -------
    ticks  : list[int]   — day offset positions
    labels : list[str]   — formatted tick labels
    """
    if x_unit == "years":
        step   = interval * 365
        def fmt(t): return f"{t // 365}y"
    elif x_unit == "months":
        step   = interval * 30
        def fmt(t): return f"{t // 30}m"
    else:  # days
        step   = interval
        def fmt(t): return f"{t}d"

    ticks  = list(range(0, max_days, step))
    labels = [fmt(t) for t in ticks]
    return ticks, labels


# ── Line panel ────────────────────────────────────────────────────────────

def render_line_panel(
    ax,
    ts:       pd.DataFrame,
    cfg,                    # ActivityOverTimeConfig
    max_days: int,
) -> None:
    """
    Render the activity line panel (top subplot).

    Parameters
    ----------
    ax : matplotlib Axes
    ts : pd.DataFrame
        Must contain 'day' and 'pct_active' columns.
    cfg : ActivityOverTimeConfig
    max_days : int
    """
    gcfg = cfg.general
    lcfg = cfg.line
    fs   = gcfg.font_size

    ax.plot(
        ts["day"], ts["pct_active"],
        color     = lcfg.color,
        linewidth = lcfg.linewidth,
        zorder    = 3,
    )

    if lcfg.fill_alpha > 0:
        ax.fill_between(
            ts["day"], ts["pct_active"],
            alpha  = lcfg.fill_alpha,
            color  = lcfg.color,
            zorder = 2,
        )

    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fraction active", fontsize=fs)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(
            lambda x, _: f"{x:.0%}"
        )
    )
    ax.tick_params(axis="both", labelsize=fs - 1)

    title = gcfg.title or "Activity over time"
    ax.set_title(title, fontsize=gcfg.title_font_size)

    ticks, labels = build_xticks(max_days, gcfg.x_unit, gcfg.x_interval)
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=fs - 1)
    ax.set_xlim(0, max_days)


# ── Arrow / diverging bar panel ───────────────────────────────────────────

def render_arrow_panel(
    ax,
    ts:       pd.DataFrame,
    cfg,                    # ActivityOverTimeConfig
    max_days: int,
) -> None:
    """
    Render the entry/exit panel (bottom subplot).

    Style "bar"     — diverging bar chart (entered up, exited down)
    Style "scatter" — proportional arrow markers (legacy)

    Parameters
    ----------
    ax : matplotlib Axes
    ts : pd.DataFrame
        Must contain 'day', 'n_entered', 'n_exited' columns.
    cfg : ActivityOverTimeConfig
    max_days : int
    """
    gcfg = cfg.general
    acfg = cfg.arrows
    fs   = gcfg.font_size

    valid = ts.dropna(subset=["n_entered", "n_exited"]).copy()
    valid["n_entered"] = valid["n_entered"].astype(float)
    valid["n_exited"]  = valid["n_exited"].astype(float)

    # Zero reference line
    ax.axhline(y=0, color=acfg.zero_line_color, linewidth=0.8, zorder=1)

    if valid.empty:
        ax.set_yticks([0])
        return

    if acfg.style == "bar":
        _render_diverging_bars(ax, valid, acfg, fs)
    else:
        _render_scatter_arrows(ax, valid, acfg, fs)

    ax.tick_params(axis="x", labelsize=fs - 1)
    ax.set_xlabel(
        f"Time ({gcfg.x_unit} from observation start)",
        fontsize=fs
    )
    ax.set_xlim(0, max_days)

    ticks, labels = build_xticks(max_days, gcfg.x_unit, gcfg.x_interval)
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=fs - 1)


def _render_diverging_bars(ax, valid: pd.DataFrame, acfg, fs: int) -> None:
    """Diverging bar chart — entered bars go up, exited bars go down."""
    days     = valid["day"].values
    entered  = valid["n_entered"].values
    exited   = valid["n_exited"].values

    # Bar width — fraction of median tick gap
    if len(days) > 1:
        gaps  = np.diff(np.sort(days))
        width = float(np.median(gaps[gaps > 0])) * acfg.bar_width
    else:
        width = acfg.bar_width

    # Entered — positive (up)
    mask_e = entered > 0
    if mask_e.any():
        ax.bar(
            days[mask_e],
            entered[mask_e],
            width     = width,
            color     = acfg.entered_color,
            alpha     = 0.85,
            zorder    = 2,
            label     = "Entered active",
        )

    # Exited — negative (down)
    mask_x = exited > 0
    if mask_x.any():
        ax.bar(
            days[mask_x],
            -exited[mask_x],
            width     = width,
            color     = acfg.exited_color,
            alpha     = 0.85,
            zorder    = 2,
            label     = "Exited active",
        )

    # Y axis — show absolute values
    if acfg.show_y_axis:
        max_val = max(entered.max(), exited.max(), 1)
        ax.set_ylim(-max_val * 1.3, max_val * 1.3)
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{int(abs(x))}")
        )
        ax.set_ylabel("Count", fontsize=fs)

        # Label each side
        ax.text(
            0.01, 0.97, "Entered ↑",
            transform=ax.transAxes, fontsize=fs - 2,
            color=acfg.entered_color, va="top",
        )
        ax.text(
            0.01, 0.03, "Exited ↓",
            transform=ax.transAxes, fontsize=fs - 2,
            color=acfg.exited_color, va="bottom",
        )
    else:
        ax.set_yticks([])

    ax.tick_params(axis="y", labelsize=fs - 1)


def _render_scatter_arrows(ax, valid: pd.DataFrame, acfg, fs: int) -> None:
    """Legacy scatter arrow markers — proportional size."""
    entered = valid["n_entered"].astype(float)
    exited  = valid["n_exited"].astype(float)
    max_val = max(entered.max(), exited.max(), 1)

    def scale(s):
        return acfg.min_size + (s / max_val) * (acfg.max_size - acfg.min_size)

    axis_y = 0.5

    mask_e = entered > 0
    if mask_e.any():
        ax.scatter(
            valid.loc[mask_e, "day"],
            [axis_y + 0.15] * mask_e.sum(),
            s      = scale(entered[mask_e]),
            marker = "^",
            color  = acfg.entered_color,
            zorder = 3,
            label  = "Entered active",
        )

    mask_x = exited > 0
    if mask_x.any():
        ax.scatter(
            valid.loc[mask_x, "day"],
            [axis_y - 0.15] * mask_x.sum(),
            s      = scale(exited[mask_x]),
            marker = "v",
            color  = acfg.exited_color,
            zorder = 3,
            label  = "Exited active",
        )

    ax.set_ylim(0, 1)
    ax.set_yticks([])
