"""
events_within_obs_period_analyzer_utils.py
Utility functions used by `EventsWithinObsPeriodsAnalyzer`.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

_ERROR_PREFIX = "[events_within_obs_period_analyzer_utils] Error"
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


def _pipe_dates(timestamps) -> str:
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

    Fully vectorized — no entity-level for loops.

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
    """
    spans = _validate_span_df(span_df, entity_col, span_start_col, span_end_col)

    # ------------------------------------------------------------------ #
    # Step 1 — join events to spans, filter to overlapping, clip
    # ------------------------------------------------------------------ #
    if events_df.empty or entity_col not in events_df.columns:
        merged = pd.DataFrame(columns=[entity_col, start_col, end_col,
                                       "span_start", "span_end"])
    else:
        ev = events_df[[entity_col, start_col, end_col]].copy()
        ev[start_col] = pd.to_datetime(ev[start_col])
        ev[end_col]   = pd.to_datetime(ev[end_col])

        # Join spans onto events
        merged = ev.merge(spans[[entity_col, "span_start", "span_end"]],
                          on=entity_col, how="inner")

        # Keep only events overlapping the span
        overlaps = (merged[start_col] < merged["span_end"]) & \
                   (merged[end_col]   > merged["span_start"])
        merged = merged[overlaps].copy()

        # Clip to span boundaries
        merged["clipped_start"] = merged[[start_col, "span_start"]].max(axis=1)
        merged["clipped_end"]   = merged[[end_col,   "span_end"]].min(axis=1)

    # ------------------------------------------------------------------ #
    # Step 2 — aggregate per entity
    # ------------------------------------------------------------------ #
    days = lambda td_series: td_series.dt.total_seconds() / 86400

    if merged.empty:
        # No events overlap any span — all entities have no coverage
        result = spans.copy()
        result["span_duration_days"] = days(result["span_end"] - result["span_start"])
        for col in ["active_days", "inactive_days",
                    "inactive_days_before_first_event",
                    "inactive_days_after_last_event",
                    "inactive_days_middle",
                    "first_event_start", "last_event_end",
                    "event_starts", "event_ends"]:
            result[col] = pd.NA
        return result.reset_index(drop=True)

    # Active days per entity — sum of clipped interval lengths
    merged["_active"] = days(merged["clipped_end"] - merged["clipped_start"])
    active = merged.groupby(entity_col)["_active"].sum().rename("active_days")

    # First / last clipped boundaries per entity
    first_start = merged.groupby(entity_col)["clipped_start"].min().rename("first_event_start")
    last_end    = merged.groupby(entity_col)["clipped_end"].max().rename("last_event_end")

    # Pipe-delimited event_starts / event_ends — vectorized string join
    merged_sorted = merged.sort_values([entity_col, "clipped_start"])
    merged_sorted["_s"] = merged_sorted["clipped_start"].dt.strftime(_DATE_FMT)
    merged_sorted["_e"] = merged_sorted["clipped_end"].dt.strftime(_DATE_FMT)

    event_starts_s = merged_sorted.groupby(entity_col)["_s"].agg(" | ".join).rename("event_starts")
    event_ends_s   = merged_sorted.groupby(entity_col)["_e"].agg(" | ".join).rename("event_ends")

    # ------------------------------------------------------------------ #
    # Step 3 — assemble result from spans, joining aggregated metrics
    # ------------------------------------------------------------------ #
    result = spans.copy()
    result["span_duration_days"] = days(result["span_end"] - result["span_start"])

    result = result.join(active,       on=entity_col)
    result = result.join(first_start,  on=entity_col)
    result = result.join(last_end,     on=entity_col)
    result = result.join(event_starts_s, on=entity_col)
    result = result.join(event_ends_s,   on=entity_col)

    # ------------------------------------------------------------------ #
    # Step 4 — compute inactive breakdown (vectorized)
    # ------------------------------------------------------------------ #
    covered = result["active_days"].notna()

    result["inactive_days"] = pd.NA
    result.loc[covered, "inactive_days"] = (
        result.loc[covered, "span_duration_days"] -
        result.loc[covered, "active_days"]
    )

    result["inactive_days_before_first_event"] = pd.NA
    result.loc[covered, "inactive_days_before_first_event"] = days(
        result.loc[covered, "first_event_start"] -
        result.loc[covered, "span_start"]
    )

    result["inactive_days_after_last_event"] = pd.NA
    result.loc[covered, "inactive_days_after_last_event"] = days(
        result.loc[covered, "span_end"] -
        result.loc[covered, "last_event_end"]
    )

    result["inactive_days_middle"] = pd.NA
    result.loc[covered, "inactive_days_middle"] = (
        result.loc[covered, "inactive_days"] -
        result.loc[covered, "inactive_days_before_first_event"] -
        result.loc[covered, "inactive_days_after_last_event"]
    )

    # Column order
    col_order = [
        entity_col, "span_start", "span_end", "span_duration_days",
        "active_days", "inactive_days",
        "inactive_days_before_first_event",
        "inactive_days_after_last_event",
        "inactive_days_middle",
        "first_event_start", "last_event_end",
        "event_starts", "event_ends",
    ]
    return result[col_order].reset_index(drop=True)
