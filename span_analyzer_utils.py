"""
span_analyzer_utils.py
Utility functions used by `EventsWithinSpansAnalyzer`.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[span_analyzer_utils] Error"
_DATE_FMT = "%Y-%m-%d"


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _validate_span_df(
    span_df: pd.DataFrame,
    entity_col: str,
    span_start_col: str,
    span_end_col: str,
) -> pd.DataFrame:
    if not isinstance(span_df, pd.DataFrame):
        raise TypeError(
            f"{_ERROR_PREFIX} in _validate_span_df: expected a DataFrame, "
            f"got {type(span_df).__name__}"
        )

    required = {entity_col, span_start_col, span_end_col}
    missing = required - set(span_df.columns)
    if missing:
        raise ValueError(
            f"{_ERROR_PREFIX} in _validate_span_df: missing columns {sorted(missing)}"
        )

    out = span_df[[entity_col, span_start_col, span_end_col]].copy()
    out = out.rename(columns={span_start_col: "span_start", span_end_col: "span_end"})

    if out[entity_col].isna().any():
        raise ValueError(
            f"{_ERROR_PREFIX} in _validate_span_df: '{entity_col}' contains null values"
        )
    if out[entity_col].duplicated().any():
        dups = out.loc[out[entity_col].duplicated(), entity_col].unique().tolist()
        raise ValueError(
            f"{_ERROR_PREFIX} in _validate_span_df: duplicate entity values: {dups}"
        )

    try:
        out["span_start"] = pd.to_datetime(out["span_start"])
        out["span_end"]   = pd.to_datetime(out["span_end"])
    except Exception as exc:
        raise TypeError(
            f"{_ERROR_PREFIX} in _validate_span_df: span columns must be datetime-like — {exc}"
        ) from exc

    if out["span_start"].isna().any() or out["span_end"].isna().any():
        raise ValueError(
            f"{_ERROR_PREFIX} in _validate_span_df: span_start/span_end cannot contain nulls"
        )

    invalid = out["span_start"] > out["span_end"]
    if invalid.any():
        bad = out.loc[invalid, entity_col].tolist()
        raise ValueError(
            f"{_ERROR_PREFIX} in _validate_span_df: span_start > span_end for entities {bad}"
        )

    return out.reset_index(drop=True)


def _timedelta_to_days(td: pd.Timedelta) -> float:
    return td.total_seconds() / 86400


def _active_days_within_span(
    entity_events: pd.DataFrame,
    span_start: pd.Timestamp,
    span_end: pd.Timestamp,
    start_col: str,
    end_col: str,
) -> float | None:
    overlapping = entity_events[
        (entity_events[start_col] < span_end) &
        (entity_events[end_col] > span_start)
    ]

    if overlapping.empty:
        return None  # signals "no events in span"

    clipped_start = overlapping[start_col].clip(lower=span_start)
    clipped_end   = overlapping[end_col].clip(upper=span_end)
    active = (clipped_end - clipped_start).apply(_timedelta_to_days).sum()

    return active


def _pipe_dates(timestamps: list[pd.Timestamp]) -> str:
    """Format a list of timestamps as a pipe-delimited string."""
    return " | ".join(t.strftime(_DATE_FMT) for t in timestamps)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def compute_activity_inactivity(
    events_df: pd.DataFrame,
    span_df: pd.DataFrame,
    entity_col: str,
    start_col: str,
    end_col: str,
    span_start_col: str = "span_start",
    span_end_col: str = "span_end",
) -> pd.DataFrame:
    """
    Compute active vs. inactive days for each entity within their span.

    Parameters
    ----------
    events_df : pd.DataFrame
        Merged (non-overlapping) events. One or more rows per entity.
    span_df : pd.DataFrame
        One row per entity defining their span window.
    entity_col : str
        Column identifying the entity in both DataFrames.
    start_col : str
        Event start time column in events_df.
    end_col : str
        Event end time column in events_df.
    span_start_col : str
        Span start column in span_df. Default 'span_start'.
    span_end_col : str
        Span end column in span_df. Default 'span_end'.

    Returns
    -------
    pd.DataFrame
        One row per entity with columns:
        [entity_col, span_start, span_end, span_duration_days,
         active_days, inactive_days,
         inactive_days_before_first_event,
         inactive_days_after_last_event,
         inactive_days_middle,
         first_event_start, last_event_end,
         event_starts, event_ends]

        event_starts / event_ends are pipe-delimited strings of the
        clipped interval boundaries, one token per merged interval.
        Both are NA for entities with no events overlapping their span.
    """
    spans = _validate_span_df(span_df, entity_col, span_start_col, span_end_col)

    grouped = {}
    if not events_df.empty and entity_col in events_df.columns:
        grouped = {
            entity: group
            for entity, group in events_df.groupby(entity_col)
        }

    rows = []
    for _, span_row in spans.iterrows():
        entity             = span_row[entity_col]
        span_start         = span_row["span_start"]
        span_end           = span_row["span_end"]
        span_duration_days = _timedelta_to_days(span_end - span_start)

        entity_events = grouped.get(entity, pd.DataFrame(columns=[start_col, end_col]))

        in_span = entity_events[
            (entity_events[start_col] < span_end) &
            (entity_events[end_col]   > span_start)
        ]

        active_days = _active_days_within_span(
            entity_events, span_start, span_end, start_col, end_col
        )

        if active_days is None:
            rows.append({
                entity_col:                         entity,
                "span_start":                       span_start,
                "span_end":                         span_end,
                "span_duration_days":               span_duration_days,
                "active_days":                      pd.NA,
                "inactive_days":                    pd.NA,
                "inactive_days_before_first_event": pd.NA,
                "inactive_days_after_last_event":   pd.NA,
                "inactive_days_middle":             pd.NA,
                "first_event_start":                pd.NA,
                "last_event_end":                   pd.NA,
                "event_starts":                     pd.NA,
                "event_ends":                       pd.NA,
            })
            continue

        inactive_days = span_duration_days - active_days

        first_event_start = max(in_span[start_col].min(), span_start)
        last_event_end    = min(in_span[end_col].max(),   span_end)

        before = _timedelta_to_days(first_event_start - span_start)
        after  = _timedelta_to_days(span_end - last_event_end)
        middle = inactive_days - before - after

        # Build clipped interval lists for visualization
        clipped_starts = in_span[start_col].clip(lower=span_start).tolist()
        clipped_ends   = in_span[end_col].clip(upper=span_end).tolist()

        rows.append({
            entity_col:                         entity,
            "span_start":                       span_start,
            "span_end":                         span_end,
            "span_duration_days":               span_duration_days,
            "active_days":                      active_days,
            "inactive_days":                    inactive_days,
            "inactive_days_before_first_event": before,
            "inactive_days_after_last_event":   after,
            "inactive_days_middle":             middle,
            "first_event_start":                first_event_start,
            "last_event_end":                   last_event_end,
            "event_starts":                     _pipe_dates(clipped_starts),
            "event_ends":                       _pipe_dates(clipped_ends),
        })

    return pd.DataFrame(rows).reset_index(drop=True)