"""
event_primitives_utils.py
Primitive operations shared across all event analysis utils.
No dependencies on other eventus utils files.

Functions
---------
parse_dates(value, obs_start, obs_end)
    Parse a pipe-delimited date string into a sorted list of
    pd.Timestamps, filtered to the obs window.

compute_gaps(dates)
    Compute a numpy array of consecutive gap lengths in days
    from a sorted list of pd.Timestamps.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any


def parse_dates(
    value:     Any,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> list[pd.Timestamp]:
    """
    Parse a pipe-delimited event date string into a sorted list
    of pd.Timestamps, retaining only dates within [obs_start, obs_end].

    Parameters
    ----------
    value : Any
        Raw cell value from the evt_{identity} column.
        Expected format: "2020-01-01 | 2020-06-15 | 2021-03-10"
        NaN / None returns an empty list.
    obs_start : pd.Timestamp
        Observation period start (inclusive), normalized to midnight.
    obs_end : pd.Timestamp
        Observation period end (inclusive), normalized to midnight.

    Returns
    -------
    list[pd.Timestamp]
        Sorted list of valid timestamps within the obs window.
        Empty list if value is NaN or no dates fall within the window.

    Notes
    -----
    - Unparseable tokens are silently skipped.
    - Dates outside [obs_start, obs_end] are silently excluded.
    - Returned timestamps are normalized to midnight.
    """
    if pd.isna(value):
        return []
    dates = []
    for token in str(value).split(" | "):
        try:
            ts = pd.Timestamp(token.strip()).normalize()
            if obs_start <= ts <= obs_end:
                dates.append(ts)
        except Exception:
            continue
    return sorted(dates)


def compute_gaps(dates: list[pd.Timestamp]) -> np.ndarray:
    """
    Compute consecutive gap lengths in days from a sorted list of
    pd.Timestamps.

    Parameters
    ----------
    dates : list[pd.Timestamp]
        Sorted list of event timestamps. Must have at least 2
        elements to produce a non-empty result.

    Returns
    -------
    np.ndarray
        1-D float array of gap lengths in days.
        Shape: (len(dates) - 1,).
        Empty array if len(dates) < 2.

    Notes
    -----
    - Assumes dates are already sorted ascending.
    - Gap values are always non-negative integers cast to float.
    """
    if len(dates) < 2:
        return np.array([], dtype=float)
    return np.array(
        [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)],
        dtype=float,
    )
