"""
events_utils.py
Utility functions used by the Events class.
"""
from __future__ import annotations
import pandas as pd
from .event_semantics import EventSemantics


def merge_overlapping_events(
    events_df: pd.DataFrame,
    semantics: EventSemantics,
    meaningful_gap: int = 0,
) -> pd.DataFrame:
    """
    Merge overlapping or adjacent events for each entity into non-overlapping
    intervals. Optionally bridges small gaps between consecutive events.
 
    Only columns declared in semantics are kept. Optional columns
    (event_id_col, event_type_col, metadata_cols) are pipe-aggregated
    across merged rows.
 
    Parameters
    ----------
    events_df : pd.DataFrame
        Valid events (output of Events.data — no nulls in core columns).
    semantics : EventSemantics
        Declares which columns exist and what they mean.
    meaningful_gap : int
        Gaps between consecutive events <= this many days are treated as
        contiguous and merged. Default 0 (only overlapping/touching events
        are merged).
 
    Returns
    -------
    pd.DataFrame
        Non-overlapping events with the same column structure as the input,
        limited to semantics-declared columns.
    """
    entity_col = semantics.entity_id_col
    start_col  = semantics.start_time_col
    end_col    = semantics.end_time_col
 
    optional_cols = []
    if semantics.event_id_col:   optional_cols.append(semantics.event_id_col)
    if semantics.event_type_col: optional_cols.append(semantics.event_type_col)
    optional_cols.extend(semantics.metadata_cols)
 
    keep_cols = [entity_col, start_col, end_col] + optional_cols
    df = events_df[[c for c in keep_cols if c in events_df.columns]].copy()
 
    gap_threshold = pd.Timedelta(days=meaningful_gap)
 
    merged_rows = []
    for entity, group in df.groupby(entity_col):
        group = group.sort_values(start_col, kind="mergesort").reset_index(drop=True)
 
        current_start = group.at[0, start_col]
        current_end   = group.at[0, end_col]
        current_opt   = {col: [str(group.at[0, col])] for col in optional_cols if col in df.columns}
 
        for _, row in group.iloc[1:].iterrows():
            gap = row[start_col] - current_end
            if gap <= gap_threshold:
                # Overlapping, touching, or within meaningful_gap — merge
                current_end = max(current_end, row[end_col])
                for col in optional_cols:
                    if col in df.columns:
                        current_opt[col].append(str(row[col]))
            else:
                # Gap too large — save current interval and start a new one
                merged_rows.append(_build_row(
                    entity, current_start, current_end, current_opt,
                    entity_col, start_col, end_col, optional_cols, df
                ))
                current_start = row[start_col]
                current_end   = row[end_col]
                current_opt   = {col: [str(row[col])] for col in optional_cols if col in df.columns}
 
        merged_rows.append(_build_row(
            entity, current_start, current_end, current_opt,
            entity_col, start_col, end_col, optional_cols, df
        ))
 
    return pd.DataFrame(merged_rows).reset_index(drop=True)
 
 
def _build_row(
    entity,
    start: pd.Timestamp,
    end: pd.Timestamp,
    optionals: dict,
    entity_col: str,
    start_col: str,
    end_col: str,
    optional_cols: list,
    df: pd.DataFrame,
) -> dict:
    row = {entity_col: entity, start_col: start, end_col: end}
    for col in optional_cols:
        if col in df.columns:
            row[col] = " | ".join(optionals[col])
    return row
 
 
def clip_events_to_spans(
    events_df: pd.DataFrame,
    spans_df: pd.DataFrame,
    entity_col: str,
    start_col: str,
    end_col: str,
    span_start_col: str,
    span_end_col: str,
    ignore_entities_with_no_span: bool = False,
) -> pd.DataFrame:
    """
    Clip events to their entity's span boundaries.
 
    For each event:
    - If it overlaps the span: clip start/end to span boundaries and keep it.
    - If it falls entirely outside the span: drop it.
 
    Parameters
    ----------
    events_df : pd.DataFrame
        Valid events with entity_col, start_col, end_col.
    spans_df : pd.DataFrame
        One row per entity with entity_col, span_start_col, span_end_col.
    entity_col : str
        Column identifying the entity in both DataFrames.
    start_col : str
        Event start time column in events_df.
    end_col : str
        Event end time column in events_df.
    span_start_col : str
        Span start column in spans_df.
    span_end_col : str
        Span end column in spans_df.
    ignore_entities_with_no_span : bool
        If True, events for entities with no span are silently dropped.
        If False (default), raises ValueError listing which entities
        are missing spans (up to 10 examples).
 
    Returns
    -------
    pd.DataFrame
        Events clipped to span boundaries. Same columns as events_df.
        Rows entirely outside the span are dropped.
        Rows for entities with no span are dropped (if ignore_entities_with_no_span=True)
        or raise (if False).
    """
    # Build span lookup: entity -> (span_start, span_end)
    span_lookup = spans_df.set_index(entity_col)[[span_start_col, span_end_col]]
 
    # Check for entities in events with no span
    event_entities  = set(events_df[entity_col].dropna().unique())
    span_entities   = set(span_lookup.index)
    missing_spans   = event_entities - span_entities
 
    if missing_spans:
        if not ignore_entities_with_no_span:
            examples = sorted(missing_spans)[:10]
            raise ValueError(
                f"[clip_events_to_spans] Error: the following entities have events "
                f"but no span defined (showing up to 10): {examples}"
            )
        # Drop events for entities with no span
        events_df = events_df[events_df[entity_col].isin(span_entities)].copy()
 
    if events_df.empty:
        return events_df.copy()
 
    # Merge span boundaries onto events
    merged = events_df.merge(
        span_lookup.rename(columns={
            span_start_col: "_span_start",
            span_end_col:   "_span_end",
        }),
        left_on=entity_col,
        right_index=True,
        how="left",
    )
 
    # Drop events entirely outside the span
    overlaps = (
        (merged[start_col] < merged["_span_end"]) &
        (merged[end_col]   > merged["_span_start"])
    )
    merged = merged[overlaps].copy()
 
    # Clip to span boundaries
    merged[start_col] = merged[[start_col, "_span_start"]].max(axis=1)
    merged[end_col]   = merged[[end_col,   "_span_end"]].min(axis=1)
 
    # Drop helper columns and reset index
    merged = merged.drop(columns=["_span_start", "_span_end"])
    return merged.reset_index(drop=True)