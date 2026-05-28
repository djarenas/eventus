"""
cohort_timeline_event_analyzer_utils.py
Workhorse helpers for CohortTimelineEventAnalyzer.
No class state — only data inputs and outputs.

Functions
---------
validate_max_n(max_n)
    Raise if max_n is not a valid integer >= 1.

base_data(ct, identity)
    Parse obs period and return (data, series, obs_start, obs_end).

build_result_data(ct, data, stats_df, obs_start, obs_end)
    Assemble entity_col + obs cols + computed stats into one DataFrame.

build_survival_arrays(series, obs_start, obs_end)
    Return (obs_duration, time_to_first) arrays for KM computation.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

import eventus.intermediates.survival_result_utils as survival_utils

_ERROR = "[CohortTimelineEventAnalyzer] Error"


# ------------------------------------------------------------------ #
# Validation
# ------------------------------------------------------------------ #

def validate_max_n(max_n: int) -> None:
    """
    Raise if max_n is not a valid integer >= 1.

    Parameters
    ----------
    max_n : int
        Maximum nth event to compute timing for.

    Raises
    ------
    TypeError
        If max_n is not an int.
    ValueError
        If max_n < 1.
    """
    if not isinstance(max_n, int):
        raise TypeError(
            f"{_ERROR} max_n must be an integer, "
            f"got {type(max_n).__name__}"
        )
    if max_n < 1:
        raise ValueError(
            f"{_ERROR} max_n must be >= 1, got {max_n}"
        )


# ------------------------------------------------------------------ #
# Data setup
# ------------------------------------------------------------------ #

def base_data(
    ct,
    identity: str,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Parse the obs period columns and return the raw data needed by
    every compute/enrich method.

    Parameters
    ----------
    ct : CohortTimeline
    identity : str
        Event identity to extract.

    Returns
    -------
    data : pd.DataFrame
        Full CohortTimeline data copy.
    series : pd.Series
        Raw evt_{identity} column.
    obs_start : pd.Series
        Per-entity obs start, normalized to midnight.
    obs_end : pd.Series
        Per-entity obs end, normalized to midnight.
    """
    data      = ct.data
    obs_start = pd.to_datetime(data["obs_start"]).dt.normalize()
    obs_end   = pd.to_datetime(data["obs_end"]).dt.normalize()
    series    = data[f"evt_{identity}"]
    return data, series, obs_start, obs_end


def build_result_data(
    ct,
    data:      pd.DataFrame,
    stats_df:  pd.DataFrame,
    obs_start: pd.Series,
    obs_end:   pd.Series,
) -> pd.DataFrame:
    """
    Assemble the result DataFrame returned by compute_* methods:
    entity_col + obs_start + obs_end + computed stats.

    Parameters
    ----------
    ct : CohortTimeline
    data : pd.DataFrame
        Full CohortTimeline data (source of entity_col values).
    stats_df : pd.DataFrame
        Computed stats, one row per entity, aligned to data.
    obs_start : pd.Series
        Parsed obs start series.
    obs_end : pd.Series
        Parsed obs end series.

    Returns
    -------
    pd.DataFrame
        One row per entity.
    """
    result = data[[ct.entity_col]].copy()
    result["obs_start"] = obs_start.values
    result["obs_end"]   = obs_end.values
    for col in stats_df.columns:
        result[col] = stats_df[col].values
    return result


# ------------------------------------------------------------------ #
# Survival setup
# ------------------------------------------------------------------ #

def build_survival_arrays(
    series:    pd.Series,
    obs_start: pd.Series,
    obs_end:   pd.Series,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the obs_duration and time_to_first arrays needed for KM
    computation.

    Entities with no event get NaN in time_to_first and are treated
    as right-censored at obs_duration_days.

    Parameters
    ----------
    series : pd.Series
        Raw evt_{identity} column (pipe-delimited date strings).
    obs_start : pd.Series
        Per-entity obs start timestamps.
    obs_end : pd.Series
        Per-entity obs end timestamps.

    Returns
    -------
    obs_duration : np.ndarray of float
        Days from obs_start to obs_end, one value per entity.
    time_to_first : np.ndarray of float
        Days from obs_start to first event; NaN if no event occurred.
    """
    obs_duration = (obs_end - obs_start).dt.days.values.astype(float)
    time_to_first = np.array([
        survival_utils._time_to_first(val, s, e)
        for val, s, e in zip(series, obs_start, obs_end)
    ], dtype=float)
    return obs_duration, time_to_first
