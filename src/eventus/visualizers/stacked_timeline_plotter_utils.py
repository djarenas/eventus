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
import matplotlib.ticker as ticker
from collections import defaultdict

from eventus.intermediates.cohort_timeline_utils import OBS_START_COL, OBS_END_COL

_WARN_PREFIX = "[StackedTimelinePlotter]"


# ── X-axis resolution ─────────────────────────────────────────────────────

def resolve_x_mode(data: pd.DataFrame, x_axis: str) -> str:
    """
    Determine whether to use calendar or normalized x-axis.

    Parameters
    ----------
    data : pd.DataFrame
        Must contain obs_start and obs_end columns (parsed as dates).
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
        data[OBS_START_COL].nunique() == 1 and
        data[OBS_END_COL].nunique() == 1
    )

    if x_axis == "calendar":
        if not uniform:
            raise ValueError(
                f"[StackedTimelinePlotter] Error: x_axis='calendar' requires "
                f"all entities to have the same observation period. Found "
                f"{data[OBS_START_COL].nunique()} different obs_start values. "
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


# ── Obs period lookup ─────────────────────────────────────────────────────

def build_obs_lookup(
    data:       pd.DataFrame,
    entity_col: str,
) -> dict:
    """
    Build {entity: (obs_start, obs_end, obs_days)} lookup.

    Parameters
    ----------
    data : pd.DataFrame
        Must have obs_start and obs_end columns already parsed as dates.
    entity_col : str
        Entity identifier column name.

    Returns
    -------
    dict
        {entity_id: (pd.Timestamp, pd.Timestamp, int)}
    """
    return {
        row[entity_col]: (
            row[OBS_START_COL],
            row[OBS_END_COL],
            (row[OBS_END_COL] - row[OBS_START_COL]).days,
        )
        for _, row in data.iterrows()
    }


# ── Segment parsing ───────────────────────────────────────────────────────

def parse_segments(
    row:            pd.Series,
    obs_start:      pd.Timestamp,
    obs_end:        pd.Timestamp,
    obs_days:       int,
    episode_identity: str | None,
    ev_color:       str,
    poi,
) -> list[tuple[float, float, str]]:
    """
    Parse pipe-delimited episode strings into (left, width, color) tuples
    in day-offset coordinates.

    Uses eps_{identity}_starts and eps_{identity}_ends columns if
    episode_identity is provided. Falls back to color_no_episodes if no
    episodes are found.

    Parameters
    ----------
    row : pd.Series
        One row from the intermediate DataFrame.
    obs_start, obs_end : pd.Timestamp
        Observation period boundaries.
    obs_days : int
        Length of observation period in days.
    episode_identity : str | None
        Identity of the episode layer. Used to locate eps_{identity}_starts
        and eps_{identity}_ends columns. None means no episode layer.
    ev_color : str
        Color for active episode segments.
    poi : POIConfig
        Period of interest color settings.

    Returns
    -------
    list of (left_days, width_days, color)
    """
    starts_col = f"eps_{episode_identity}_starts" if episode_identity else None
    ends_col   = f"eps_{episode_identity}_ends"   if episode_identity else None

    has_episodes = (
        episode_identity is not None and
        starts_col in row.index and
        not pd.isna(row.get(starts_col))
    )

    if not has_episodes:
        return [(0, obs_days, poi.color_no_episodes)]

    starts_raw = str(row[starts_col]).split(" | ")
    ends_raw   = str(row[ends_col]).split(" | ")

    intervals = []
    for s, e in zip(starts_raw, ends_raw):
        try:
            ev_start = pd.Timestamp(s.strip()).normalize()
            ev_end   = pd.Timestamp(e.strip()).normalize()
        except Exception:
            continue
        if ev_start < obs_end and ev_end > obs_start:
            intervals.append((
                max(ev_start, obs_start),
                min(ev_end,   obs_end),
            ))

    if not intervals:
        return [(0, obs_days, poi.color_no_episodes)]

    intervals.sort(key=lambda x: x[0])
    segments      = []
    prev_end_days = 0.0
    is_first      = True

    for ev_start, ev_end in intervals:
        left  = (ev_start - obs_start).days
        right = (ev_end   - obs_start).days
        width = right - left

        if left > prev_end_days:
            gap_w = left - prev_end_days
            color = poi.color_before if is_first else poi.color_middle
            segments.append((prev_end_days, gap_w, color))

        if width > 0:
            segments.append((left, width, ev_color))

        prev_end_days = max(prev_end_days, right)
        is_first      = False

    if prev_end_days < obs_days:
        segments.append((prev_end_days, obs_days - prev_end_days, poi.color_after))

    return segments


# ── Precomputation ────────────────────────────────────────────────────────

def precompute(
    entities:       list,
    data:           pd.DataFrame,
    entity_col:     str,
    obs_lookup:     dict,
    episode_identity: str | None,
    ev_color:       str,
    evt_cfg_map:    dict,
    poi,
    bar_h:          float,
    jitter:         bool  = False,
    jitter_ratio:   float = 0.01,
) -> tuple[dict, dict]:
    """
    Pre-compute all segment and marker data for all entities.

    Parameters
    ----------
    obs_lookup : dict
        {entity: (obs_start, obs_end, obs_days)}
    episode_identity : str | None
        Identity for eps_{identity}_starts/ends columns. None = no episodes.
    jitter : bool
        Apply horizontal jitter to event markers. Default False.
    jitter_ratio : float
        Jitter as fraction of obs_days. Default 0.01.

    Returns
    -------
    color_segments : dict
        {color: [(xstart, xwidth, y_center), ...]}
    marker_groups : dict
        {(color, marker, size, alpha): [(x, y_min, y_max), ...]}
    """
    rng = np.random.default_rng(42)

    entity_index = {
        entity: data[data[entity_col] == entity].iloc[0]
        for entity in entities
        if (data[entity_col] == entity).any()
    }

    color_segments: dict[str, list] = defaultdict(list)
    marker_groups:  dict[tuple, list] = defaultdict(list)

    for i, entity in enumerate(entities):
        obs_start, obs_end, obs_days = obs_lookup[entity]
        row = entity_index.get(entity)

        # ── Segments ─────────────────────────────────────────────────
        segs = parse_segments(
            row            = row if row is not None else pd.Series(),
            obs_start      = obs_start,
            obs_end        = obs_end,
            obs_days       = obs_days,
            episode_identity = episode_identity,
            ev_color       = ev_color,
            poi            = poi,
        )
        for left, width, color in segs:
            if width > 0:
                color_segments[color].append((left, width, i))

        # ── Event markers ────────────────────────────────────────
        if row is None:
            continue

        jitter_magnitude = obs_days * jitter_ratio if jitter else 0.0

        for col, ocfg in evt_cfg_map.items():
            val = row.get(col)
            if pd.isna(val):
                continue
            for token in str(val).split(" | "):
                try:
                    d = pd.Timestamp(token.strip()).normalize()
                except Exception:
                    continue
                if obs_start <= d <= obs_end:
                    x_pos = (d - obs_start).days
                    if jitter_magnitude > 0:
                        x_pos = float(np.clip(
                            x_pos + rng.uniform(-jitter_magnitude, jitter_magnitude),
                            0, obs_days,
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
    month = dt.month - 1 + n
    year  = dt.year + month // 12
    month = month % 12 + 1
    return dt.replace(year=year, month=month, day=1)


def _advance_years(dt: pd.Timestamp, n: int) -> pd.Timestamp:
    return dt.replace(year=dt.year + n, month=1, day=1)


def format_xaxis(
    ax,
    x_mode:         str,
    max_days:       int,
    span_start_ref: pd.Timestamp | None,
    font_size:      int,
    x_cfg,
) -> None:
    """Apply x-axis ticks and labels."""
    unit     = x_cfg.unit
    interval = x_cfg.interval

    if x_mode == "calendar" and span_start_ref is not None:
        if unit == "months":
            tick_dates = []
            d = span_start_ref.replace(day=1)
            while (d - span_start_ref).days <= max_days:
                tick_dates.append(d)
                d = _advance_months(d, interval)
        elif unit == "years":
            tick_dates = []
            d = span_start_ref.replace(month=1, day=1)
            while (d - span_start_ref).days <= max_days:
                tick_dates.append(d)
                d = _advance_years(d, interval)
        else:
            tick_offsets = range(0, max_days + 1, interval)
            tick_dates   = [
                span_start_ref + pd.Timedelta(days=t) for t in tick_offsets
            ]

        ticks  = [(d - span_start_ref).days for d in tick_dates]
        labels = [d.strftime(x_cfg.format) for d in tick_dates]
        ax.set_xlabel("Date", fontsize=font_size)

    else:
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
