"""
episode_event_interaction_analyzer_utils.py
Workhorse helpers for EpisodeEventInteractionAnalyzer.
No class state — only data inputs and outputs.

Key functions
-------------
parse_events(row, event_identity)
    Parse pipe-delimited event dates from one CohortTimeline row.

classify_events(events, intervals, obs_start, obs_end)
    Classify each event date into before / during / gap / after.

compute_interaction_stats(data, entity_col, episode_identity, event_identity)
    Compute per-entity segment counts for the full cohort.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import NamedTuple


_ERROR = "[EpisodeEventInteractionAnalyzer] Error"


# ── Column name helpers ────────────────────────────────────────────────────────

def eps_starts_col(identity: str) -> str: return f"eps_{identity}_starts"
def eps_ends_col(identity: str) -> str:   return f"eps_{identity}_ends"
def evt_col(identity: str) -> str:        return f"evt_{identity}"


# ── Episode parsing (reused from episode analyzer utils) ──────────────────────

def _parse_intervals(
    row:      pd.Series,
    identity: str,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Parse pipe-delimited starts/ends into (start, end) pairs."""
    if pd.isna(row.get(eps_starts_col(identity))):
        return []
    intervals = []
    for s, e in zip(
        str(row[eps_starts_col(identity)]).split(" | "),
        str(row[eps_ends_col(identity)]).split(" | "),
    ):
        try:
            intervals.append((
                pd.Timestamp(s.strip()).normalize(),
                pd.Timestamp(e.strip()).normalize(),
            ))
        except Exception:
            continue
    return intervals


def _clip_intervals(
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]],
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    clipped = []
    for s, e in intervals:
        cs = max(s, obs_start)
        ce = min(e, obs_end)
        if ce > cs:
            clipped.append((cs, ce))
    return clipped


def _merge_intervals(
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_ivs[0]]
    for s, e in sorted_ivs[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


# ── Event parsing ─────────────────────────────────────────────────────────────

def parse_events(
    row:            pd.Series,
    event_identity: str,
) -> list[pd.Timestamp]:
    """Parse pipe-delimited event dates from one CohortTimeline row."""
    col = evt_col(event_identity)
    if pd.isna(row.get(col)):
        return []
    dates = []
    for d in str(row[col]).split(" | "):
        try:
            dates.append(pd.Timestamp(d.strip()).normalize())
        except Exception:
            continue
    return dates


# ── Event classification ──────────────────────────────────────────────────────

class SegmentCounts(NamedTuple):
    n_before:      int   # events before first episode start
    n_during:      int   # events during active episodes
    n_gaps:        int   # events during gaps between episodes
    n_after:       int   # events after last episode end
    n_no_episodes: int   # events for members with no episodes (0 if has episodes)
    has_episodes:  bool  # True if member has at least one episode


def classify_events(
    events:    list[pd.Timestamp],
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]],
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> SegmentCounts:
    """
    Classify each event date relative to the episode structure.

    Parameters
    ----------
    events    : list of event dates (already clipped to obs period upstream)
    intervals : merged, clipped episode intervals for this entity
    obs_start : entity obs period start
    obs_end   : entity obs period end

    Returns
    -------
    SegmentCounts namedtuple
    """
    if not intervals:
        return SegmentCounts(
            n_before=0, n_during=0, n_gaps=0, n_after=0,
            n_no_episodes=len(events), has_episodes=False,
        )

    first_start = intervals[0][0]
    last_end    = intervals[-1][1]

    n_before = n_during = n_gaps = n_after = 0

    for ev in events:
        if ev < first_start:
            n_before += 1
        elif ev >= last_end:
            n_after += 1
        else:
            # between first_start and last_end — check if during episode or in gap
            in_episode = any(s <= ev < e for s, e in intervals)
            if in_episode:
                n_during += 1
            else:
                n_gaps += 1

    return SegmentCounts(
        n_before=n_before, n_during=n_during, n_gaps=n_gaps,
        n_after=n_after, n_no_episodes=0, has_episodes=True,
    )


# ── Main computation ──────────────────────────────────────────────────────────

def compute_interaction_stats(
    data:             pd.DataFrame,
    entity_col:       str,
    episode_identity: str,
    event_identity:   str,
) -> pd.DataFrame:
    """
    Compute per-entity segment counts for the full cohort.

    Returns
    -------
    pd.DataFrame
        One row per entity. Columns: n_before, n_during, n_gaps,
        n_after, n_no_episodes. NaN where semantically absent.
    """
    rows = []

    for _, row in data.iterrows():
        obs_start = pd.Timestamp(row["obs_start"]).normalize()
        obs_end   = pd.Timestamp(row["obs_end"]).normalize()

        intervals = _parse_intervals(row, episode_identity)
        clipped   = _clip_intervals(intervals, obs_start, obs_end) if intervals else []
        merged    = _merge_intervals(clipped) if clipped else []

        events = [
            ev for ev in parse_events(row, event_identity)
            if obs_start <= ev <= obs_end
        ]

        counts = classify_events(events, merged, obs_start, obs_end)

        if counts.has_episodes:
            rows.append({
                "n_before":      counts.n_before,
                "n_during":      counts.n_during,
                "n_gaps":        counts.n_gaps,
                "n_after":       counts.n_after,
                "n_no_episodes": pd.NA,
            })
        else:
            rows.append({
                "n_before":      pd.NA,
                "n_during":      pd.NA,
                "n_gaps":        pd.NA,
                "n_after":       pd.NA,
                "n_no_episodes": counts.n_no_episodes,
            })

    return pd.DataFrame(rows)
