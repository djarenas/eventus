"""
cohort_timeline_event_analyzer_utils.py
All utilities for CohortTimelineEventAnalyzer — guards, column helpers,
coverage computation, activity over time, and tier summaries.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from eventus.intermediates.event_activity_over_time import EventActivityOverTime

_ERROR = "[CohortTimelineEventAnalyzer] Error"
_WARNING = "[CohortTimelineEventAnalyzer] Warning"
_OBS_START_TOLERANCE_FOR_CALENDAR_MODE = 2

# ------------------------------------------------------------------ #
# Column name helpers
# ------------------------------------------------------------------ #

def evt_starts_col(identity: str) -> str:  return f"evt_{identity}_starts"
def evt_ends_col(identity: str) -> str:    return f"evt_{identity}_ends"
def active_col(identity: str) -> str:      return f"evt_{identity}_active_days"
def inactive_col(identity: str) -> str:    return f"evt_{identity}_inactive_days"
def before_col(identity: str) -> str:      return f"evt_{identity}_inactive_days_before_first_event"
def after_col(identity: str) -> str:       return f"evt_{identity}_inactive_days_after_last_event"
def middle_col(identity: str) -> str:      return f"evt_{identity}_inactive_days_middle"
def first_col(identity: str) -> str:       return f"evt_{identity}_first_start"
def last_col(identity: str) -> str:        return f"evt_{identity}_last_end"

# ------------------------------------------------------------------ #
# Guards
# ------------------------------------------------------------------ #

def require_obs_period(has_obs_period: bool) -> None:
    if not has_obs_period:
        raise ValueError(
            f"{_ERROR} CohortTimeline has no observation period. "
            f"obs_start and obs_end are required to compute event coverage."
        )

def require_identity_present(identity: str, event_identities: list[str]) -> None:
    if identity not in event_identities:
        raise ValueError(
            f"{_ERROR} identity '{identity}' not found in "
            f"event_identities: {event_identities}"
        )

def is_coverage_already_analyzed(identity: str, columns: list[str]) -> bool:
    col = active_col(identity)
    if col in columns:
        return True
    return False

def require_coverage_exists(identity: str, columns: list[str], method: str) -> None:
    col = active_col(identity)
    if col not in columns:
        raise ValueError(
            f"{_ERROR} .{method}() requires '{col}'. "
            f"Call compute_coverage() first."
        )

# ------------------------------------------------------------------ #
# compute_coverage
# ------------------------------------------------------------------ #

def _parse_intervals(row: pd.Series, identity: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Parse pipe-delimited starts/ends from one row into a list of
    (start, end) Timestamp pairs. Returns [] if no events.
    """
    if pd.isna(row.get(evt_starts_col(identity))):
        return []
    intervals = []
    for s, e in zip(
        str(row[evt_starts_col(identity)]).split(" | "),
        str(row[evt_ends_col(identity)]).split(" | "),
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
    """
    Clip intervals to [obs_start, obs_end] and drop zero-length results.
    """
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
    """
    Merge overlapping or adjacent intervals. Input must be non-empty.
    Returns sorted, non-overlapping list.
    """
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_ivs[0]]
    for s, e in sorted_ivs[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _compute_entity_coverage(
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]],
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> dict:
    """
    Given merged, clipped intervals and an obs period, compute all
    active/inactive day metrics for one entity.
    """
    obs_days    = (obs_end - obs_start).days
    active_days = sum((e - s).days for s, e in intervals)

    first_start = intervals[0][0]
    last_end    = intervals[-1][1]

    before_days = (first_start - obs_start).days
    after_days  = (obs_end     - last_end).days

    # Middle gaps — inactive days between first and last event
    middle_days = (
        (last_end - first_start).days
        - sum((e - s).days for s, e in intervals)
    )

    return {
        "active_days":                      float(active_days),
        "inactive_days":                    float(obs_days - active_days),
        "inactive_days_before_first_event": float(max(before_days, 0)),
        "inactive_days_after_last_event":   float(max(after_days,  0)),
        "inactive_days_middle":             float(max(middle_days, 0)),
        "first_start":                      first_start,
        "last_end":                         last_end,
    }


def compute_coverage(
    data:       pd.DataFrame,
    entity_col: str,
    identity:   str,
) -> pd.DataFrame:
    """
    Compute active/inactive day columns for evt_{identity} within each
    entity's observation period. Works directly on the CohortTimeline
    DataFrame — no intermediate objects.

    Returns the input DataFrame with analysis columns appended.
    All columns are NA for entities with no events in their obs period.
    """
    out = data.copy()

    results = {}
    for _, row in data.iterrows():
        entity    = row[entity_col]
        obs_start = pd.Timestamp(row["obs_start"]).normalize()
        obs_end   = pd.Timestamp(row["obs_end"]).normalize()

        intervals = _parse_intervals(row, identity)
        if not intervals:
            results[entity] = None
            continue

        clipped = _clip_intervals(intervals, obs_start, obs_end)
        if not clipped:
            results[entity] = None
            continue

        merged          = _merge_intervals(clipped)
        results[entity] = _compute_entity_coverage(merged, obs_start, obs_end)

    out[active_col(identity)]   = out[entity_col].map(lambda e: results[e]["active_days"]                      if results.get(e) else pd.NA)
    out[inactive_col(identity)] = out[entity_col].map(lambda e: results[e]["inactive_days"]                    if results.get(e) else pd.NA)
    out[before_col(identity)]   = out[entity_col].map(lambda e: results[e]["inactive_days_before_first_event"] if results.get(e) else pd.NA)
    out[after_col(identity)]    = out[entity_col].map(lambda e: results[e]["inactive_days_after_last_event"]   if results.get(e) else pd.NA)
    out[middle_col(identity)]   = out[entity_col].map(lambda e: results[e]["inactive_days_middle"]             if results.get(e) else pd.NA)
    out[first_col(identity)]    = out[entity_col].map(lambda e: results[e]["first_start"]                      if results.get(e) else pd.NaT)
    out[last_col(identity)]     = out[entity_col].map(lambda e: results[e]["last_end"]                         if results.get(e) else pd.NaT)

    return out

# ------------------------------------------------------------------ #
# activity_over_time
# ------------------------------------------------------------------ #

def _validate_obs_durations(data: pd.DataFrame, entity_col: str) -> int:
    durations = pd.to_numeric(data["obs_duration_days"].dropna(), errors="coerce")
    if durations.empty:
        raise ValueError(f"{_ERROR} no valid obs_duration_days found.")
    counts  = durations.value_counts()
    max_dur = int(durations.max())
    if len(counts) > 1:
        most_common_dur   = int(counts.index[0])
        most_common_count = int(counts.iloc[0])
        others = {int(k): int(v) for k, v in counts.iloc[1:].items()}
        print(
            f"{_WARNING}: obs durations are not equal across entities.\n"
            f"  Most common: {most_common_dur} days ({most_common_count} entities)\n"
            f"  Others: {others}\n"
            f"  Proceeding with full grid (0 to {max_dur} days)."
        )
    return max_dur


def _build_relative_intervals(
    data:       pd.DataFrame,
    entity_col: str,
    identity:   str,
) -> pd.DataFrame:
    covered = data[
        data[evt_starts_col(identity)].notna() &
        data[evt_ends_col(identity)].notna()
    ].copy()

    if covered.empty:
        return pd.DataFrame(columns=[entity_col, "start_day", "end_day"])

    rows = []
    for _, row in covered.iterrows():
        obs_start = pd.Timestamp(row["obs_start"]).normalize()
        obs_end   = pd.Timestamp(row["obs_end"]).normalize()
        obs_days  = (obs_end - obs_start).days

        for s, e in zip(
            str(row[evt_starts_col(identity)]).split(" | "),
            str(row[evt_ends_col(identity)]).split(" | "),
        ):
            try:
                ev_start  = pd.Timestamp(s.strip()).normalize()
                ev_end    = pd.Timestamp(e.strip()).normalize()
                start_day = max(0,        (ev_start - obs_start).days)
                end_day   = min(obs_days, (ev_end   - obs_start).days)
                if end_day > start_day:
                    rows.append({entity_col: row[entity_col],
                                 "start_day": start_day, "end_day": end_day})
            except Exception:
                continue

    return pd.DataFrame(rows)


def _active_at_day(intervals: pd.DataFrame, entity_col: str, day: int) -> set:
    if intervals.empty:
        return set()
    mask = (intervals["start_day"] <= day) & (intervals["end_day"] > day)
    return set(intervals.loc[mask, entity_col].unique())
  
def _return_shared_obs_start(data: pd.DataFrame, tolerance_days: int) -> pd.Timestamp:  
    """  
    Raise if obs_start differs by more than `tolerance_days` across entities.  
    Returns a shared obs_start as a normalized Timestamp (earliest date).  
    """  
    starts = pd.to_datetime(data["obs_start"]).dt.normalize()  
    min_start = starts.min()  
    max_start = starts.max()  
  
    # Calculate difference in days  
    max_diff = (max_start - min_start).days  
  
    if max_diff > tolerance_days:  
        # Find which obs_start values are outside the tolerance  
        too_early = starts[starts < min_start + pd.Timedelta(days=tolerance_days)]  
        too_late  = starts[starts > max_start - pd.Timedelta(days=tolerance_days)]  
  
        # Prepare examples (convert to strings for printing)  
        unique_starts = starts.unique()  
        example_values = sorted(str(s.date()) for s in unique_starts)  
        example_preview = ", ".join(example_values[:5])  # limit to first 5 for brevity  
  
        raise ValueError(  
            f"mode='calendar' requires obs_start within {tolerance_days} days. "  
            f"Found a range of {max_diff} days between earliest ({min_start.date()}) "  
            f"and latest ({max_start.date()}). "  
            f"Example differing values: {example_preview}"  
        )  
  
    return min_start  


def calc_activity_over_time(
    data:        pd.DataFrame,
    entity_col:  str,
    identity:    str,
    granularity: str = "month",
    mode:        str = "normalized",
) -> EventActivityOverTime:
    """
    Compute per-timepoint activity statistics and return an
    EventActivityOverTime result object.

    Parameters
    ----------
    data : pd.DataFrame
        CohortTimeline data with coverage analysis columns present.
    entity_col : str
        Entity identifier column name.
    identity : str
        Event identity.
    granularity : str
        Time resolution — 'day', 'week', or 'month'.
    mode : str
        'normalized' — day offsets relative to each entity's own obs_start.
        'calendar'   — day offsets relative to the shared cohort obs_start.
                       Raises if obs_start is not uniform across entities.

    Returns
    -------
    EventActivityOverTime
    """
    if granularity not in {"day", "week", "month"}:
        raise ValueError(
            f"{_ERROR} granularity must be 'day', 'week', or 'month', "
            f"got '{granularity}'"
        )
    if mode not in {"normalized", "calendar"}:
        raise ValueError(
            f"{_ERROR} mode must be 'normalized' or 'calendar', "
            f"got '{mode}'"
        )

    cohort_start = None
    if mode == "calendar":
        cohort_start = _return_shared_obs_start(data, _OBS_START_TOLERANCE_FOR_CALENDAR_MODE)

    max_dur   = _validate_obs_durations(data, entity_col)
    n_total   = len(data)
    step      = {"day": 1, "week": 7, "month": 30}[granularity]
    intervals = _build_relative_intervals(data, entity_col, identity)
    day_grid  = list(range(0, max_dur + 1, step))

    rows = []
    prev_active = None
    for day in day_grid:
        active_set = _active_at_day(intervals, entity_col, day)
        n_active   = len(active_set)
        rows.append({
            "day":        day,
            "n_total":    n_total,
            "n_active":   n_active,
            "pct_active": round(n_active / n_total, 4) if n_total > 0 else 0.0,
            "n_entered":  pd.NA if prev_active is None else len(active_set - prev_active),
            "n_exited":   pd.NA if prev_active is None else len(prev_active - active_set),
        })
        prev_active = active_set

    ts = pd.DataFrame(rows).reset_index(drop=True)
    return EventActivityOverTime(data=ts, mode=mode, cohort_start=cohort_start)

# ------------------------------------------------------------------ #
# Tier summaries
# ------------------------------------------------------------------ #

def _pct(n: int, denom: int) -> float:
    return round(100 * n / denom, 1) if denom > 0 else 0.0

def _count_pct(n: int, denom: int) -> dict:
    return {"n": int(n), "pct": float(_pct(n, denom))}

def _stats(series: pd.Series, percentiles: list[int]) -> dict:
    clean = series.dropna()
    if clean.empty:
        return {"mean": None, **{f"p{p}": None for p in percentiles}}
    return {
        "mean": round(float(clean.mean()), 1),
        **{f"p{p}": round(float(np.percentile(clean, p)), 1) for p in percentiles},
    }

def _covered(data: pd.DataFrame, identity: str) -> pd.DataFrame:
    return data[data[active_col(identity)].notna()].copy()


def calc_tier1(data: pd.DataFrame, entity_col: str, identity: str) -> dict:
    total     = len(data)
    n_covered = int(data[active_col(identity)].notna().sum())
    return {
        "# denominator: total entities": None,
        "t1_total_entities": total,
        "t1_no_coverage":    _count_pct(total - n_covered, total),
        "t1_any_coverage":   _count_pct(n_covered,         total),
    }


def calc_tier2(data: pd.DataFrame, entity_col: str, identity: str) -> dict:
    cov       = _covered(data, identity)
    n_covered = len(cov)
    if n_covered == 0:
        return {"# denominator: entities with any coverage": None,
                "t2_no_covered_entities": True}

    span   = cov["obs_duration_days"]
    active = cov[active_col(identity)]
    before = cov[before_col(identity)]
    after  = cov[after_col(identity)]
    middle = cov[middle_col(identity)]

    full       = active >= span
    entered    = before > 0
    exited     = after  > 0
    has_middle = middle > 0

    return {
        "# denominator: entities with any coverage (t1_any_coverage)": None,
        "t2_full_coverage":                 _count_pct(int(full.sum()),                              n_covered),
        "t2_entered_during_obs":            _count_pct(int(entered.sum()),                           n_covered),
        "t2_exited_during_obs":             _count_pct(int(exited.sum()),                            n_covered),
        "t2_has_middle_gaps":               _count_pct(int(has_middle.sum()),                        n_covered),
        "t2_entered_late_and_exited_early": _count_pct(int((entered & exited).sum()),                n_covered),
        "t2_entered_late_and_has_gaps":     _count_pct(int((entered & has_middle).sum()),            n_covered),
        "t2_exited_early_and_has_gaps":     _count_pct(int((exited  & has_middle).sum()),            n_covered),
        "t2_clean_entry_exit_gaps_only":    _count_pct(int((~entered & ~exited & has_middle).sum()), n_covered),
    }


def calc_tier3(
    data:        pd.DataFrame,
    entity_col:  str,
    identity:    str,
    percentiles: list[int] = [25, 50, 75],
) -> dict:
    cov        = _covered(data, identity)
    before_pos = cov[cov[before_col(identity)] > 0]
    after_pos  = cov[cov[after_col(identity)]  > 0]
    middle_pos = cov[cov[middle_col(identity)] > 0]

    return {
        "# denominator: entities with any coverage unless noted": None,
        "t3_active_days":   _stats(cov[active_col(identity)],   percentiles),
        "t3_inactive_days": _stats(cov[inactive_col(identity)], percentiles),
        f"t3_inactive_days_before_first_event (n={len(before_pos)})":
            _stats(before_pos[before_col(identity)], percentiles),
        f"t3_inactive_days_after_last_event (n={len(after_pos)})":
            _stats(after_pos[after_col(identity)], percentiles),
        f"t3_inactive_days_middle (n={len(middle_pos)})":
            _stats(middle_pos[middle_col(identity)], percentiles),
    }
