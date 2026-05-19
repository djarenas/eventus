"""
merge_utils.py
Utility functions for merging overlapping or adjacent event intervals.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.semantics.event_semantics import EventSemantics
from eventus.cleaners.merge_config import MergeConfig


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _aggregate_category(values: list[str], rule: str) -> str:
    """
    Aggregate a list of category values into a pipe-delimited string.

    "sequence" — all values in order, including duplicates.
    "unique"   — unique values only, alphabetical order.
    """
    clean = [v for v in values if v not in ("nan", "None", "")]
    if not clean:
        return ""
    if rule == "unique":
        return " | ".join(sorted(set(clean)))
    return " | ".join(clean)


def _aggregate_numeric(values: list[str], rule: str) -> float | None:
    """Aggregate a list of numeric string values into a scalar."""
    nums = []
    for v in values:
        try:
            nums.append(float(v))
        except (ValueError, TypeError):
            pass
    if not nums:
        return None
    arr = np.array(nums)
    if rule == "mean":     return float(np.mean(arr))
    if rule == "median":   return float(np.median(arr))
    if rule == "min":      return float(np.min(arr))
    if rule == "max":      return float(np.max(arr))
    if rule == "variance": return float(np.var(arr))
    return None


def _aggregate_col(
    values:        list[str],
    col:           str,
    merge_cfg:     MergeConfig,
    semantics:     EventSemantics,
) -> str | float | None:
    """
    Aggregate values for one descriptor column.

    Uses the aggregation rule from MergeConfig and the type from
    EventSemantics.descriptor_cols.
    Falls back to sequence for columns not declared in MergeConfig.
    """
    rule = merge_cfg.descriptor_cols.get(col)
    if rule is None:
        # Not declared in merge config — default to sequence
        return _aggregate_category(values, "sequence")

    # Get type from semantics
    col_type = (
        semantics.descriptor_cols[col].type
        if semantics.descriptor_cols and col in semantics.descriptor_cols
        else "category"
    )

    if col_type == "numeric":
        return _aggregate_numeric(values, rule)
    return _aggregate_category(values, rule)


# ── Build one merged row ──────────────────────────────────────────────────────

def _build_merged_row(
    entity:         object,
    group_key:      dict,
    start:          pd.Timestamp,
    end:            pd.Timestamp,
    collected:      dict[str, list[str]],
    entity_col:     str,
    start_col:      str,
    end_col:        str,
    merge_cfg:      MergeConfig,
    semantics:      EventSemantics,
    agg_cols:       list[str],
) -> dict:
    """Build one merged row dict from collected values."""
    row = {entity_col: entity, start_col: start, end_col: end}
    row.update(group_key)
    for col in agg_cols:
        row[col] = _aggregate_col(collected[col], col, merge_cfg, semantics)
    return row


# ── Main merge function ───────────────────────────────────────────────────────

def merge_overlapping_events(
    events_df: pd.DataFrame,
    semantics: EventSemantics,
    merge_cfg: MergeConfig,
) -> pd.DataFrame:
    """
    Merge overlapping or adjacent events per entity into non-overlapping
    intervals.

    Two intervals are eligible for merging only if:
      - They belong to the same entity, AND
      - All EventSemantics.also_defined_by columns have the same value, AND
      - The gap between them is <= merge_cfg.meaningful_gap_days

    Descriptor columns declared in merge_cfg.descriptor_cols are
    aggregated according to their rules. Descriptor columns not declared
    in merge_cfg are pipe-aggregated using sequence as a fallback.

    Parameters
    ----------
    events_df : pd.DataFrame
        Valid events — no nulls in core columns.
    semantics : EventSemantics
        Declares column names, also_defined_by, and descriptor_cols.
    merge_cfg : MergeConfig
        Gap threshold and descriptor aggregation rules.

    Returns
    -------
    pd.DataFrame
        Non-overlapping events, limited to semantics-declared columns.
    """
    entity_col      = semantics.entity_id_col
    start_col       = semantics.start_time_col
    end_col         = semantics.end_time_col
    also_defined_by = semantics.also_defined_by or []

    # Columns to aggregate — descriptor_cols only
    descriptor_keys = list(semantics.descriptor_cols.keys()) \
        if semantics.descriptor_cols else []
    agg_cols = [col for col in descriptor_keys if col in events_df.columns]

    # Group by entity + also_defined_by
    group_cols = [entity_col] + [
        col for col in also_defined_by if col in events_df.columns
    ]

    keep_cols = list(dict.fromkeys(
        [entity_col, start_col, end_col] + also_defined_by + agg_cols
    ))
    df = events_df[[c for c in keep_cols if c in events_df.columns]].copy()

    gap_threshold = pd.Timedelta(days=merge_cfg.meaningful_gap_days)
    merged_rows   = []

    for group_values, group in df.groupby(group_cols, sort=False):
        # Reconstruct group key for also_defined_by columns
        if isinstance(group_values, tuple):
            entity    = group_values[0]
            group_key = {
                col: val
                for col, val in zip(group_cols[1:], group_values[1:])
            }
        else:
            entity    = group_values
            group_key = {}

        group = group.sort_values(start_col, kind="mergesort").reset_index(drop=True)

        current_start = group.at[0, start_col]
        current_end   = group.at[0, end_col]
        collected     = {
            col: [str(group.at[0, col])]
            for col in agg_cols
        }

        for _, row in group.iloc[1:].iterrows():
            gap = row[start_col] - current_end
            if gap <= gap_threshold:
                current_end = max(current_end, row[end_col])
                for col in agg_cols:
                    collected[col].append(str(row[col]))
            else:
                merged_rows.append(_build_merged_row(
                    entity, group_key, current_start, current_end,
                    collected, entity_col, start_col, end_col,
                    merge_cfg, semantics, agg_cols,
                ))
                current_start = row[start_col]
                current_end   = row[end_col]
                collected     = {col: [str(row[col])] for col in agg_cols}

        merged_rows.append(_build_merged_row(
            entity, group_key, current_start, current_end,
            collected, entity_col, start_col, end_col,
            merge_cfg, semantics, agg_cols,
        ))

    if not merged_rows:
        return df.iloc[0:0].copy()

    return pd.DataFrame(merged_rows).reset_index(drop=True)
