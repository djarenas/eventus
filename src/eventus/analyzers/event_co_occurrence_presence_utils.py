"""
event_co_occurrence_presence_utils.py
Per-entity presence and same-day co-occurrence computation for
EventCoOccurrenceAnalyzer.compute_presence().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.analyzers.event_co_occurrence_primitives import (
    build_co_occurrence_streams,
    parse_event_dates,
)


def compute_entity_presence(
    dates_a:     list,
    dates_b:     list,
    within_days: int,
) -> dict:
    """
    Compute all presence statistics for one entity.

    Parameters
    ----------
    dates_a     : Sorted list of A event timestamps within obs window.
    dates_b     : Sorted list of B event timestamps within obs window.
    within_days : Non-negative integer window for co-occurrence count.
                  0 = same-day pairs only.

    Returns
    -------
    dict with all presence columns.
    """
    n_a = len(dates_a)
    n_b = len(dates_b)

    has_a    = n_a > 0
    has_b    = n_b > 0
    has_both = has_a and has_b

    # ── Same-day ──────────────────────────────────────────────────────
    set_a = set(dates_a)
    set_b = set(dates_b)
    same_days = set_a & set_b
    n_same_day = len(same_days)

    # pct of A events with a same-day B
    pct_a_with_same_day_b = (
        round(100.0 * sum(1 for d in dates_a if d in set_b) / n_a, 2)
        if n_a > 0 else np.nan
    )
    # pct of B events with a same-day A
    pct_b_with_same_day_a = (
        round(100.0 * sum(1 for d in dates_b if d in set_a) / n_b, 2)
        if n_b > 0 else np.nan
    )

    # ── Co-occurrence within window ───────────────────────────────────
    if not has_a and not has_b:
        n_co_occurrences_within = np.nan
    elif within_days == 0:
        # Same-day pair count — one pair per (a_event, b_event) on same day
        n_co_occurrences_within = sum(
            1 for a in dates_a for b in dates_b if a == b
        )
    else:
        # Count (A, B) pairs where |a - b| <= within_days (either direction)
        n_co_occurrences_within = sum(
            1
            for a in dates_a
            for b in dates_b
            if abs((a - b).days) <= within_days
        )

    return {
        "n_a":                     n_a,
        "n_b":                     n_b,
        "has_a":                   has_a,
        "has_b":                   has_b,
        "has_both":                has_both,
        "n_same_day":              n_same_day,
        "pct_a_with_same_day_b":   pct_a_with_same_day_b,
        "pct_b_with_same_day_a":   pct_b_with_same_day_a,
        "n_co_occurrences_within": n_co_occurrences_within,
    }


def compute_presence_stats(
    data:        pd.DataFrame,
    entity_col:  str,
    evt_col_a:   str,
    evt_col_b:   str,
    within_days: int,
) -> pd.DataFrame:
    """
    Compute presence statistics for all entities.

    Parameters
    ----------
    data        : CohortTimeline.data
    entity_col  : Entity identifier column name.
    evt_col_a   : evt_{identity_a} column name.
    evt_col_b   : evt_{identity_b} column name.
    within_days : Window for n_co_occurrences_within.

    Returns
    -------
    pd.DataFrame
        One row per entity with all presence columns.
    """
    rows = []
    obs_start_col = "obs_start"
    obs_end_col   = "obs_end"

    for _, row in data.iterrows():
        obs_start = pd.Timestamp(row[obs_start_col]).normalize()
        obs_end   = pd.Timestamp(row[obs_end_col]).normalize()

        dates_a, dates_b = build_co_occurrence_streams(
            row, evt_col_a, evt_col_b, obs_start, obs_end
        )

        stats = compute_entity_presence(dates_a, dates_b, within_days)
        stats[entity_col]    = row[entity_col]
        stats[obs_start_col] = obs_start
        stats[obs_end_col]   = obs_end
        rows.append(stats)

    return pd.DataFrame(rows)
