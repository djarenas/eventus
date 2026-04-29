"""
stacked_timeline_plotter_utils.py
Pure utility functions for StackedTimelinePlotter.
No class state — only data and config inputs.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict

_WARN_PREFIX = "[StackedTimelinePlotter]"
_VALID_X_UNITS = {"days", "months", "years"}


# ── X-axis resolution ─────────────────────────────────────────────────────

def resolve_x_mode(data: pd.DataFrame, x_axis: str) -> str:
    """
    Determine whether to use calendar or normalized x-axis.

    Parameters
    ----------
    data : pd.DataFrame
        Must contain span_start and span_end columns (parsed as dates).
    x_axis : str
        "auto", "calendar", or "normalized".

    Returns
    -------
    str
        "calendar" or "normalized".
    """
    if x_axis == "normalized":
        return "normalized"

    uniform = (
        data["span_start"].nunique() == 1 and
        data["span_end"].nunique() == 1
    )

    if x_axis == "calendar":
        if not uniform:
            raise ValueError(
                f"[StackedTimelinePlotter] Error: x_axis='calendar' requires "
                f"all entities to have the same observation period. Found "
                f"{data['span_start'].nunique()} different span_start values. "
                f"Use x_axis='auto' or x_axis='normalized' instead."
            )
        return "calendar"

    # auto
    if not uniform:
        warnings.warn(
            f"{_WARN_PREFIX} Observation periods differ across entities — "
            f"using normalized x-axis (day 0 = obs_start per entity). "
            f"Set x_axis: 'calendar' in config to override "
            f"(requires uniform periods).",
            UserWarning, stacklevel=3,
        )
        return "normalized"
    return "calendar"


# ── Span lookup ───────────────────────────────────────────────────────────

def build_span_lookup(
    data:       pd.DataFrame,
    entity_col: str,
) -> dict:
    """
    Build {entity: (span_start, span_end, span_days)} lookup.

    Parameters
    ----------
    data : pd.DataFrame
        Must have span_start and span_end columns already parsed as dates.
    entity_col : str
        Entity identifier column name.

    Returns
    -------
    dict
        {entity_id: (pd.Timestamp, pd.Timestamp, int)}
    """
    return {
        row[entity_col]: (
            row["span_start"],
            row["span_end"],
            (row["span_end"] - row["span_start"]).days,
        )
        for _, row in data.iterrows()
    }


# ── Segment parsing ───────────────────────────────────────────────────────

def parse_segments(
    row:        pd.Series,
    span_start: pd.Timestamp,
    span_end:   pd.Timestamp,
    span_days:  int,
    has_events: bool,
    ev_color:   str,
    poi,                    # POIConfig
) -> list[tuple[float, float, str]]:
    """
    Parse pipe-delimited event strings into (left, width, color) tuples
    in day-offset coordinates.

    Segments cover the full span width:
      color_before    — inactive before first event
      ev_color        — active event intervals
      color_middle    — gaps between events
      color_after     — inactive after last event
      color_no_events — full bar when entity has no events

    Parameters
    ----------
    row : pd.Series
        One row from the intermediate DataFrame.
    span_start, span_end : pd.Timestamp
        Observation period boundaries.
    span_days : int
        Length of observation period in days.
    has_events : bool
        Whether the intermediate has event columns at all.
    ev_color : str
        Color for active event segments.
    poi : POIConfig
        Period of interest color settings.

    Returns
    -------
    list of (left_days, width_days, color)
    """
    if not has_events or pd.isna(row.get("event_starts")):
        return [(0, span_days, poi.color_no_events)]

    starts_raw = str(row["event_starts"]).split(" | ")
    ends_raw   = str(row["event_ends"]).split(" | ")

    intervals = []
    for s, e in zip(starts_raw, ends_raw):
        try:
            ev_start = pd.Timestamp(s.strip()).normalize()
            ev_end   = pd.Timestamp(e.strip()).normalize()
        except Exception:
            continue
        if ev_start < span_end and ev_end > span_start:
            intervals.append((
                max(ev_start, span_start),
                min(ev_end,   span_end),
            ))

    if not intervals:
        return [(0, span_days, poi.color_no_events)]

    intervals.sort(key=lambda x: x[0])
    segments      = []
    prev_end_days = 0.0
    is_first      = True

    for ev_start, ev_end in intervals:
        left  = (ev_start - span_start).days
        right = (ev_end   - span_start).days
        width = right - left

        if left > prev_end_days:
            gap_w = left - prev_end_days
            color = poi.color_before if is_first else poi.color_middle
            segments.append((prev_end_days, gap_w, color))

        if width > 0:
            segments.append((left, width, ev_color))

        prev_end_days = max(prev_end_days, right)
        is_first      = False

    if prev_end_days < span_days:
        segments.append((prev_end_days, span_days - prev_end_days, poi.color_after))

    return segments


# ── Precomputation ────────────────────────────────────────────────────────

def precompute(
    entities:     list,
    data:         pd.DataFrame,
    entity_col:   str,
    span_lookup:  dict,
    has_events:   bool,
    ev_color:     str,
    occ_cfg_map:  dict,
    poi,                      # POIConfig
    bar_h:        float,
    jitter:       bool  = False,
    jitter_ratio: float = 0.01,
) -> tuple[dict, dict]:
    """
    Pre-compute all segment and marker data for all entities.

    Parameters
    ----------
    jitter : bool
        If True, apply horizontal jitter to occurrence markers so
        that overlapping occurrences on the same day are visible.
        Default False.
    jitter_ratio : float
        Jitter magnitude as a ratio of each entity's span_days.
        e.g. 0.01 = 1% of the observation period. Default 0.01.
        Jittered positions are clipped to [0, span_days].

    Returns
    -------
    color_segments : dict
        {color: [(xstart, xwidth, y_center), ...]}
    marker_groups : dict
        {(color, marker, size, alpha): [(x, y_min, y_max), ...]}
    """
    import numpy as np

    rng = np.random.default_rng(42)

    # Pre-index rows by entity for O(1) lookup
    entity_index = {
        entity: data[data[entity_col] == entity].iloc[0]
        for entity in entities
        if (data[entity_col] == entity).any()
    }

    color_segments: dict[str, list] = defaultdict(list)
    marker_groups:  dict[tuple, list] = defaultdict(list)

    for i, entity in enumerate(entities):
        span_start, span_end, span_days = span_lookup[entity]
        row = entity_index.get(entity)

        # ── Segments ─────────────────────────────────────────────────
        segs = parse_segments(
            row        = row if row is not None else pd.Series(),
            span_start = span_start,
            span_end   = span_end,
            span_days  = span_days,
            has_events = has_events and row is not None,
            ev_color   = ev_color,
            poi        = poi,
        )
        for left, width, color in segs:
            if width > 0:
                color_segments[color].append((left, width, i))

        # ── Occurrence markers ────────────────────────────────────────
        if row is None:
            continue

        jitter_magnitude = span_days * jitter_ratio if jitter else 0.0

        for col, ocfg in occ_cfg_map.items():
            val = row.get(col)
            if pd.isna(val):
                continue
            for token in str(val).split(" | "):
                try:
                    d = pd.Timestamp(token.strip()).normalize()
                except Exception:
                    continue
                if span_start <= d <= span_end:
                    x_pos = (d - span_start).days
                    if jitter_magnitude > 0:
                        x_pos = float(np.clip(
                            x_pos + rng.uniform(-jitter_magnitude, jitter_magnitude),
                            0, span_days,
                        ))
                    key = (ocfg.color, ocfg.marker, ocfg.size, ocfg.alpha)
                    marker_groups[key].append((
                        x_pos,
                        i - bar_h / 2,
                        i + bar_h / 2,
                    ))

    return color_segments, marker_groups


# ── X-axis formatting ─────────────────────────────────────────────────────

def _advance_months(dt: pd.Timestamp, n: int) -> pd.Timestamp:
    """Advance a Timestamp by exactly n calendar months, anchored to day 1."""
    month = dt.month - 1 + n
    year  = dt.year + month // 12
    month = month % 12 + 1
    return dt.replace(year=year, month=month, day=1)


def _advance_years(dt: pd.Timestamp, n: int) -> pd.Timestamp:
    """Advance a Timestamp by exactly n calendar years."""
    return dt.replace(year=dt.year + n, month=1, day=1)


def format_xaxis(
    ax,
    x_mode:         str,
    max_days:       int,
    span_start_ref: pd.Timestamp | None,
    font_size:      int,
    x_cfg,          # XAxisConfig
) -> None:
    """
    Apply x-axis ticks and labels.

    In calendar mode:  ticks at actual calendar boundaries (months or years),
                       labelled with strftime format from config.
    In normalized mode: ticks labelled as Nd, Nm, or Ny.

    For months and years, ticks are generated by advancing actual calendar
    boundaries — not by multiplying by 30 or 365 — so labels never drift
    or duplicate.
    """
    unit     = x_cfg.unit
    interval = x_cfg.interval

    if x_mode == "calendar" and span_start_ref is not None:
        # ── Calendar mode — generate real calendar boundaries ─────────
        if unit == "months":
            tick_dates = []
            d = span_start_ref.replace(day=1)  # anchor to first of month
            while (d - span_start_ref).days <= max_days:
                tick_dates.append(d)
                d = _advance_months(d, interval)

        elif unit == "years":
            tick_dates = []
            d = span_start_ref.replace(month=1, day=1)  # anchor to Jan 1
            while (d - span_start_ref).days <= max_days:
                tick_dates.append(d)
                d = _advance_years(d, interval)

        else:  # days
            tick_offsets = range(0, max_days + 1, interval)
            tick_dates   = [
                span_start_ref + pd.Timedelta(days=t) for t in tick_offsets
            ]

        ticks  = [(d - span_start_ref).days for d in tick_dates]
        labels = [d.strftime(x_cfg.format) for d in tick_dates]
        ax.set_xlabel("Date", fontsize=font_size)

    else:
        # ── Normalized mode — label as offset from day 0 ──────────────
        if unit == "years":
            step = interval * 365
            def fmt(t): return f"{t // 365}y"
        elif unit == "months":
            step = interval * 30
            def fmt(t): return f"{t // 30}m"
        else:
            step = interval
            def fmt(t): return f"{t}d"

        ticks  = list(range(0, max_days + 1, step))
        labels = [fmt(t) for t in ticks]
        ax.set_xlabel("Time", fontsize=font_size)

    ax.set_xticks(ticks)
    ax.set_xticklabels(
        labels,
        fontsize = font_size - 1,
        rotation = 45,
        ha       = "right",
    )


# ── Figure size ───────────────────────────────────────────────────────────

def compute_figsize(
    n_entities:       int,
    row_height:       float,
    figsize_override: list | None = None,
) -> list[float]:
    """Compute figure size from entity count and row height."""
    if figsize_override:
        return figsize_override
    fig_h = max(2.0, n_entities * row_height + 1.5)
    return [12, fig_h]
