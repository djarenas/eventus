"""
obs_period_per_entity_utils.py
Workhorse functions for ObsPeriodPerEntity construction.
"""
from __future__ import annotations
import re
import warnings
import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta

_ERROR_PREFIX = "[obs_period_per_entity_utils] Error"


def validate_identity(identity: str) -> None:
    """
    Raise if identity contains characters other than letters,
    numbers, and underscores.
    """
    if not re.match(r'^[a-zA-Z0-9_]+$', identity):
        raise ValueError(
            f"{_ERROR_PREFIX}: identity {identity!r} contains invalid "
            f"characters. Use only letters, numbers, and underscores "
            f"e.g. 'medicaid_2022' not '{identity}'"
        )


def validate_age_window(age_start: int, age_end: int) -> None:
    """
    Raise if age window parameters are invalid.
    """
    for name, val in [("age_start", age_start), ("age_end", age_end)]:
        if not isinstance(val, int):
            raise TypeError(
                f"{_ERROR_PREFIX}: {name} must be an integer, "
                f"got {type(val).__name__}"
            )
        if not (0 <= val <= 120):
            raise ValueError(
                f"{_ERROR_PREFIX}: {name} must be between 0 and 120, "
                f"got {val}"
            )
    if age_start >= age_end:
        raise ValueError(
            f"{_ERROR_PREFIX}: age_start ({age_start}) must be less than "
            f"age_end ({age_end})"
        )


def handle_leap_year(dob: pd.Timestamp, years: int) -> pd.Timestamp:
    """
    Add years to a date of birth, handling Feb 29 leap year birthdays.
    Feb 29 birthdays shift to Feb 28 in non-leap years.

    Parameters
    ----------
    dob : pd.Timestamp
        Date of birth.
    years : int
        Number of years to add.

    Returns
    -------
    pd.Timestamp
        The resulting date.
    """
    try:
        result = dob + relativedelta(years=years)
        return pd.Timestamp(result)
    except Exception:
        # Fallback for Feb 29 → Feb 28
        fallback = date(dob.year + years, 2, 28)
        warnings.warn(
            f"[ObsPeriodPerEntity] Feb 29 birthday {dob.date()} shifted to "
            f"Feb 28 {fallback} when adding {years} years.",
            UserWarning, stacklevel=3,
        )
        return pd.Timestamp(fallback)


def warn_future_dates(
    df:         pd.DataFrame,
    start_col:  str,
    end_col:    str,
    entity_col: str,
) -> None:
    """
    Warn if any observation period dates are in the future,
    showing specific row examples.
    """
    today = pd.Timestamp.today().normalize()

    future_start = df[df[start_col] > today]
    if not future_start.empty:
        examples = future_start[entity_col].head(3).tolist()
        warnings.warn(
            f"[ObsPeriodPerEntity] {len(future_start)} entities have "
            f"span_start in the future. "
            f"Example entity IDs: {examples}. "
            f"Is this intentional (prospective study)?",
            UserWarning, stacklevel=3,
        )

    future_end = df[df[end_col] > today]
    if not future_end.empty:
        examples = future_end[entity_col].head(3).tolist()
        warnings.warn(
            f"[ObsPeriodPerEntity] {len(future_end)} entities have "
            f"span_end in the future. "
            f"Example entity IDs: {examples}. "
            f"Is this intentional (prospective study)?",
            UserWarning, stacklevel=3,
        )


def build_calendar_spans(
    entity_ids: list,
    start:      str,
    end:        str,
    entity_col: str,
    start_col:  str,
    end_col:    str,
) -> pd.DataFrame:
    """
    Build a spans DataFrame with the same start/end dates for every entity.

    Parameters
    ----------
    entity_ids : list
        Unique entity identifiers.
    start : str
        Observation period start date (ISO format).
    end : str
        Observation period end date (ISO format).
    entity_col, start_col, end_col : str
        Column names for the output DataFrame.

    Returns
    -------
    pd.DataFrame
        One row per entity with start and end dates.
    """
    # Validate dates
    try:
        start_ts = pd.Timestamp(start)
        end_ts   = pd.Timestamp(end)
    except Exception as e:
        raise ValueError(
            f"{_ERROR_PREFIX}: invalid start or end date: {e}"
        )
    if start_ts >= end_ts:
        raise ValueError(
            f"{_ERROR_PREFIX}: start ({start}) must be before end ({end})"
        )

    # Check for duplicate entity_ids
    seen = set()
    dupes = []
    for eid in entity_ids:
        if eid in seen:
            dupes.append(eid)
        seen.add(eid)
    if dupes:
        raise ValueError(
            f"{_ERROR_PREFIX}: entity_ids contains duplicates: {dupes[:5]}"
            f"{'...' if len(dupes) > 5 else ''}. "
            f"entity_ids must be unique."
        )

    return pd.DataFrame({
        entity_col: list(entity_ids),
        start_col:  start_ts,
        end_col:    end_ts,
    })


def build_age_window_spans(
    entity_df:  pd.DataFrame,
    dob_col:    str,
    age_start:  int,
    age_end:    int,
    entity_col: str,
    start_col:  str,
    end_col:    str,
) -> pd.DataFrame:
    """
    Build a spans DataFrame where each entity's window is derived
    from their date of birth and an age range.

    Parameters
    ----------
    entity_df : pd.DataFrame
        Must contain entity_col and dob_col.
    dob_col : str
        Column containing date of birth.
    age_start : int
        Start of observation window in years.
    age_end : int
        End of observation window in years.
    entity_col, start_col, end_col : str
        Column names for the output DataFrame.

    Returns
    -------
    pd.DataFrame
        One row per entity with per-patient start and end dates.
    """
    if entity_col not in entity_df.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: entity_col '{entity_col}' not found in "
            f"entity_df. Available columns: {sorted(entity_df.columns.tolist())}"
        )
    if dob_col not in entity_df.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: dob_col '{dob_col}' not found in "
            f"entity_df. Available columns: {sorted(entity_df.columns.tolist())}"
        )

    df = entity_df[[entity_col, dob_col]].copy()

    # Raise on null DOB
    null_dob = df[df[dob_col].isna()]
    if not null_dob.empty:
        examples = null_dob[entity_col].head(3).tolist()
        raise ValueError(
            f"{_ERROR_PREFIX}: {len(null_dob)} entities have null "
            f"'{dob_col}'. All entities must have a date of birth. "
            f"Example entity IDs with null DOB: {examples}. "
            f"Fix or remove these entities before constructing "
            f"ObsPeriodPerEntity."
        )

    # Parse DOB
    df[dob_col] = pd.to_datetime(df[dob_col])

    # Compute start and end dates per entity
    df[start_col] = df[dob_col].apply(
        lambda dob: handle_leap_year(dob, age_start)
    )
    df[end_col] = df[dob_col].apply(
        lambda dob: handle_leap_year(dob, age_end)
    )

    return df[[entity_col, start_col, end_col]].reset_index(drop=True)


def build_spans_from_events(
    events_df:  pd.DataFrame,
    entity_col: str,
    start_col:  str,
    end_col:    str,
    out_start_col: str,
    out_end_col:   str,
) -> pd.DataFrame:
    """
    Build a spans DataFrame from an Events DataFrame.
    Each entity's span runs from their first event start
    to their last event end.

    This is the broadest possible observation window — it captures
    the full range of activity for each entity. If you want a narrower
    window, build the spans DataFrame manually.

    Parameters
    ----------
    events_df : pd.DataFrame
        Clean events data with entity_col, start_col, end_col.
    entity_col, start_col, end_col : str
        Column names in events_df.
    out_start_col, out_end_col : str
        Column names for the output DataFrame.

    Returns
    -------
    pd.DataFrame
        One row per entity: first event start → last event end.
    """
    agg = events_df.groupby(entity_col).agg(
        **{out_start_col: (start_col, "min"),
           out_end_col:   (end_col,   "max")}
    ).reset_index()

    return agg
