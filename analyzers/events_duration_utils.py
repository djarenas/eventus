"""
events_duration_utils.py
Workhorse functions for EventDurationAnalyzer.
"""
from __future__ import annotations
import pandas as pd
import warnings

_ERROR_PREFIX = "[events_duration_utils] Error"


def compute_durations(
    data:           pd.DataFrame,
    entity_col:     str,
    start_col:      str,
    end_col:        str,
    identity:       str | None = None,
    stratify_by:    str | None = None,
    max_categories: int        = 10,
) -> pd.DataFrame:
    """
    Compute event durations from a validated Events DataFrame.

    Parameters
    ----------
    data : pd.DataFrame
        Clean event data — must have entity_col, start_col, end_col.
    entity_col : str
        Entity identifier column.
    start_col : str
        Start date column.
    end_col : str
        End date column.
    identity : str | None
        Event identity label — carried through to output.
    stratify_by : str | None
        Column to stratify by. Nulls filled with "missing".
    max_categories : int
        Maximum allowed unique categories in stratify_by. Default 10.

    Returns
    -------
    pd.DataFrame
        Columns: entity_col, duration_days, identity (if set),
        stratify_col (if stratify_by is set).
    """
    df = data.copy()

    # Compute durations
    df["duration_days"] = (
        pd.to_datetime(df[end_col]) - pd.to_datetime(df[start_col])
    ).dt.days

    # Build output
    out_cols = [entity_col, "duration_days"]
    out = df[out_cols].copy()

    # Add identity
    if identity is not None:
        out["identity"] = identity

    # Add stratification
    if stratify_by is not None:
        validate_stratify_col(df, stratify_by, max_categories)
        out["stratify_col"] = df[stratify_by].fillna("missing").astype(str)

    return out.reset_index(drop=True)


def validate_stratify_col(
    data:           pd.DataFrame,
    stratify_by:    str,
    max_categories: int,
) -> None:
    """
    Validate that stratify_by column exists and has acceptable cardinality.

    Raises ValueError if column missing or > max_categories unique values.
    Warns if any nulls are present (they will be filled with 'missing').
    """
    if stratify_by not in data.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: stratify_by column '{stratify_by}' not found "
            f"in Events data. Available columns: {sorted(data.columns.tolist())}"
        )

    n_nulls = int(data[stratify_by].isna().sum())
    if n_nulls > 0:
        warnings.warn(
            f"[EventDurationAnalyzer] '{stratify_by}' has {n_nulls} null "
            f"value(s) — filling with 'missing'.",
            UserWarning, stacklevel=3,
        )

    n_cats = data[stratify_by].nunique(dropna=True)
    if n_cats > max_categories:
        raise ValueError(
            f"{_ERROR_PREFIX}: stratify_by column '{stratify_by}' has "
            f"{n_cats} unique categories — maximum allowed is {max_categories}. "
            f"Come on bro. Consider grouping categories before stratifying."
        )
