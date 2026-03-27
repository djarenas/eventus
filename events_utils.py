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