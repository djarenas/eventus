"""
events_duration_utils.py
Workhorse functions for EventDurationAnalyzer.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[events_duration_utils] Error"


def compute_durations(
    data:            pd.DataFrame,
    entity_col:      str,
    start_col:       str,
    end_col:         str,
    identity:        str | None  = None,
    descriptor_cols: list[str]   = None,
) -> pd.DataFrame:
    """
    Compute event durations from a validated Events DataFrame.

    Parameters
    ----------
    data : pd.DataFrame
        Clean event data — must have entity_col, start_col, end_col.
        Guaranteed structurally sound by Events constructor.
    entity_col : str
        Entity identifier column.
    start_col : str
        Start date column.
    end_col : str
        End date column.
    identity : str | None
        Event identity label — carried through to output if set.
    descriptor_cols : list[str] | None
        Additional columns to carry through. Nulls allowed.
        Validated upstream by EventDurationAnalyzer — not re-validated here.

    Returns
    -------
    pd.DataFrame
        Columns: entity_col, duration_days, [identity if set],
        [descriptor_cols if provided].
        One row per event.
    """
    if descriptor_cols is None:
        descriptor_cols = []

    df = data.copy()

    # Compute durations — start <= end guaranteed by Events causality check
    df["duration_days"] = (
        pd.to_datetime(df[end_col]) - pd.to_datetime(df[start_col])
    ).dt.days

    # Build output columns
    out_cols = [entity_col, "duration_days"]

    if identity is not None:
        df["identity"] = identity
        out_cols.append("identity")

    out_cols.extend(descriptor_cols)

    return df[out_cols].reset_index(drop=True)
