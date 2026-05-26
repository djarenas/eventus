"""
episodes_duration_utils.py
Workhorse functions for EpisodeDurationAnalyzer.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[episodes_duration_utils] Error"


def compute_durations(
    data:            pd.DataFrame,
    entity_col:      str,
    start_col:       str,
    end_col:         str,
    identity:        str | None  = None,
    descriptor_cols: list[str]   = None,
) -> pd.DataFrame:
    """
    Compute episode durations from a validated Episodes DataFrame.

    Parameters
    ----------
    data : pd.DataFrame
        Clean episode data — must have entity_col, start_col, end_col.
        Guaranteed structurally sound by Episodes constructor.
    entity_col : str
        Entity identifier column.
    start_col : str
        Start date column.
    end_col : str
        End date column.
    identity : str | None
        Episode identity label — carried through to output if set.
    descriptor_cols : list[str] | None
        Additional columns to carry through. Nulls allowed.
        Validated upstream by EpisodeDurationAnalyzer — not re-validated here.

    Returns
    -------
    pd.DataFrame
        Columns: entity_col, duration_days, [identity if set],
        [descriptor_cols if provided].
        One row per episode.
    """
    if descriptor_cols is None:
        descriptor_cols = []

    df = data.copy()

    # Compute durations — start <= end guaranteed by Episodes causality check
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
