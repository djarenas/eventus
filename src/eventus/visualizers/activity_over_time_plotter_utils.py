"""
activity_over_time_plotter_utils.py
Pure utility functions for ActivityOverTimePlotter.
No class state — only data and config inputs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker

_ERROR_PREFIX = "[ActivityOverTimePlotter]"


def _require_columns(ts: pd.DataFrame, required: set[str], context: str = "") -> None:
    missing = sorted(required - set(ts.columns))
    if missing:
        where = f" in {context}" if context else ""
        raise ValueError(
            f"Missing required columns{where}: {missing}. "
            f"Available columns: {list(ts.columns)}"
        )


# ── X-axis formatting ─────────────────────────────────────────────────────

def build_xticks(
    max_days:     int,
    x_unit:       str,
    interval:     int,
    mode:         str,
    cohort_start: pd.Timestamp | None = None,
) -> tuple[list[int], list[str], str]:
    """
    Build tick positions (day offsets) and labels.

    In 'calendar' mode, labels are formatted as actual dates using
    cohort_start + day offset. In 'normalized' mode, labels are
    relative offsets (e.g. '30d', '6m', '2y').

    Parameters
    ----------
    max_days : int
        Maximum day offset in the timeseries.
    x_unit : str
        "days", "months", or "years".
    interval : int
        Tick every N units.
    mode : str
        "calendar" or "normalized".
    cohort_start : pd.Timestamp | None
        Required when mode='calendar'.

    Returns
    -------
    ticks      : list[int]   — day offset positions
    labels     : list[str]   — formatted tick labels
    x_label    : str         — x-axis label string
    """
    if x_unit == "years":
        step = interval * 365
    elif x_unit == "months":
        step = interval * 30
    else:  # days
        step = interval

    ticks = list(range(0, max_days, step))

    if mode == "calendar" and cohort_start is not None:
        labels  = [
            (cohort_start + pd.Timedelta(days=t)).strftime("%Y-%m-%d")
            for t in ticks
        ]
        x_label = "Date"
    else:
        if x_unit == "years":
            labels = [f"{t // 365}y" for t in ticks]
        elif x_unit == "months":
            labels = [f"{t // 30}m" for t in ticks]
        else:
            labels = [f"{t}d" for t in ticks]
        x_label = f"Time ({x_unit} from observation start)"

    return ticks, labels, x_label


# ── Line panel ────────────────────────────────────────────────────────────

def render_line_panel(
    ax,
    ts:           pd.DataFrame,
    cfg,
    max_days:     int,
    mode:         str,
    cohort_start: pd.Timestamp | None = None,
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
    mode : str
        'calendar' or 'normalized'.
    cohort_start : pd.Timestamp | None
        Required when mode='calendar'.
    """
    _require_columns(ts, {"day", "pct_active"}, context="render_line_panel")

    canvas = cfg.canvas
    lcfg   = cfg.line_style
    fs     = canvas.font_size

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
        ticker.FuncFormatter(lambda x, _: f"{x:.0%}")
    )
    ax.tick_params(axis="both", labelsize=fs - 1)

    title = cfg.labels.title or "Activity over time"
    ax.set_title(title, fontsize=fs)

    ticks, labels, _ = build_xticks(
        max_days, cfg.time.x_unit, cfg.time.x_interval, mode, cohort_start
    )
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=fs - 1, rotation=45, ha="right")
    ax.set_xlim(0, max_days)


# ── Arrow / diverging bar panel ───────────────────────────────────────────

def render_arrow_panel(
    ax,
    ts:           pd.DataFrame,
    cfg,
    max_days:     int,
    mode:         str,
    cohort_start: pd.Timestamp | None = None,
) -> None:
    """
    Render the entry/exit panel (bottom subplot).

    Mode "bar"     — diverging bar chart (entered up, exited down)
    Mode "scatter" — proportional arrow markers (legacy)

    Parameters
    ----------
    ax : matplotlib Axes
    ts : pd.DataFrame
        Must contain 'day', 'n_entered', 'n_exited' columns.
    cfg : ActivityOverTimeConfig
    max_days : int
    mode : str
        'calendar' or 'normalized'.
    cohort_start : pd.Timestamp | None
        Required when mode='calendar'.
    """
    _require_columns(ts, {"day", "n_entered", "n_exited"}, context="render_arrow_panel")

    canvas = cfg.canvas
    acfg   = cfg.flow_style
    fs     = canvas.font_size

    valid = ts.dropna(subset=["n_entered", "n_exited"]).copy()
    valid["n_entered"] = valid["n_entered"].astype(float)
    valid["n_exited"]  = valid["n_exited"].astype(float)

    ax.axhline(y=0, color=acfg.zero_line_color, linewidth=0.8, zorder=1)

    if valid.empty:
        ax.set_yticks([0])
        return

    if acfg.mode == "bar":
        _render_diverging_bars(ax, valid, acfg, fs)
    else:
        _render_scatter_arrows(ax, valid, acfg, fs)

    ticks, labels, x_label = build_xticks(
        max_days, cfg.time.x_unit, cfg.time.x_interval, mode, cohort_start
    )
    ax.tick_params(axis="x", labelsize=fs - 1)
    ax.set_xlabel(x_label, fontsize=fs)
    ax.set_xlim(0, max_days)
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=fs - 1, rotation=45, ha="right")


def _render_diverging_bars(ax, valid: pd.DataFrame, acfg, fs: int) -> None:
    """Diverging bar chart — entered bars go up, exited bars go down."""
    days    = valid["day"].values
    entered = valid["n_entered"].values
    exited  = valid["n_exited"].values

    if len(days) > 1:
        gaps  = np.diff(np.sort(days))
        width = float(np.median(gaps[gaps > 0])) * acfg.bar_width
    else:
        width = acfg.bar_width

    mask_e = entered > 0
    if mask_e.any():
        ax.bar(
            days[mask_e], entered[mask_e],
            width  = width,
            color  = acfg.entered_color,
            alpha  = 0.85,
            zorder = 2,
            label  = acfg.label_entered or "Entered active",
        )

    mask_x = exited > 0
    if mask_x.any():
        ax.bar(
            days[mask_x], -exited[mask_x],
            width  = width,
            color  = acfg.exited_color,
            alpha  = 0.85,
            zorder = 2,
            label  = acfg.label_exited or "Exited active",
        )

    if acfg.show_y_axis:
        max_val = max(entered.max(), exited.max(), 1)
        ax.set_ylim(-max_val * 1.3, max_val * 1.3)
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{int(abs(x))}")
        )
        ax.set_ylabel("Count", fontsize=fs)
        ax.text(
            0.01, 0.97, f"{acfg.label_entered or 'Entered'} ↑",
            transform=ax.transAxes, fontsize=fs - 2,
            color=acfg.entered_color, va="top",
        )
        ax.text(
            0.01, 0.03, f"{acfg.label_exited or 'Exited'} ↓",
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
            label  = acfg.label_entered or "Entered active",
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
            label  = acfg.label_exited or "Exited active",
        )

    ax.set_ylim(0, 1)
    ax.set_yticks([])
