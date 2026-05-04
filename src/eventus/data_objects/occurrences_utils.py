"""
occurrences_utils.py
Utility functions used by the Occurrences class and subclasses.
"""
from __future__ import annotations
import pandas as pd
from occurrence_semantics import OccurrenceSemantics

_ERROR_PREFIX = "[occurrences_utils] Error"


def build_span_from_occurrences(
    data: pd.DataFrame,
    semantics: OccurrenceSemantics,
    span_semantics,
    window: tuple[int, int],
) -> pd.DataFrame:
    """
    Build one span per entity from occurrence dates.

    Parameters
    ----------
    data : pd.DataFrame
        Valid occurrences data — one row per entity, no nulls in date_col.
    semantics : OccurrenceSemantics
        Semantics of the occurrences object.
    span_semantics : EventSemantics
        Semantics to use for the output span DataFrame.
        entity_id_col must match semantics.entity_id_col.
    window : tuple[int, int]
        (before_days, after_days) — both positive integers.
        span_start = occurrence_date - before_days
        span_end   = occurrence_date + after_days

    Returns
    -------
    pd.DataFrame
        One row per entity with columns:
        [entity_id_col, span_start_col, span_end_col]
    """
    before_days, after_days = window

    if not isinstance(before_days, int) or before_days < 0:
        raise ValueError(
            f"{_ERROR_PREFIX} in build_span_from_occurrences: "
            f"before_days must be a non-negative integer, got {before_days}"
        )
    if not isinstance(after_days, int) or after_days < 0:
        raise ValueError(
            f"{_ERROR_PREFIX} in build_span_from_occurrences: "
            f"after_days must be a non-negative integer, got {after_days}"
        )
    if before_days == 0 and after_days == 0:
        raise ValueError(
            f"{_ERROR_PREFIX} in build_span_from_occurrences: "
            f"window (0, 0) produces zero-length spans — "
            f"at least one of before_days or after_days must be > 0"
        )

    entity_col     = semantics.entity_id_col
    date_col       = semantics.date_col
    span_start_col = span_semantics.start_time_col
    span_end_col   = span_semantics.end_time_col

    dates = pd.to_datetime(data[date_col])

    out = pd.DataFrame({
        entity_col:     data[entity_col].values,
        span_start_col: dates - pd.Timedelta(days=before_days),
        span_end_col:   dates + pd.Timedelta(days=after_days),
    })

    return out.reset_index(drop=True)
