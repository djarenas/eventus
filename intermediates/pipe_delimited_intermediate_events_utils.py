"""
pipe_delimited_intermediate_events_utils.py
Utility functions for PipeDelimitedIntermediateEventAnalysis.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

_ERROR_PREFIX = "[pipe_delimited_intermediate_events_utils] Error"


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _validate_span_durations(data: pd.DataFrame, entity_col: str) -> int:
    """Warn if span durations differ. Returns max span duration in days."""
    durations = data["span_duration_days"].dropna()
    durations = pd.to_numeric(durations, errors='coerce')
    if durations.empty:
        raise ValueError(f"{_ERROR_PREFIX}: no valid span_duration_days found")

    counts = durations.value_counts()
    max_dur = int(durations.max())

    if len(counts) > 1:
        most_common_dur   = int(counts.index[0])
        most_common_count = int(counts.iloc[0])
        others = {int(k): int(v) for k, v in counts.iloc[1:].items()}
        print(
            f"Warning: span durations are not equal across entities.\n"
            f"  Most common span : {most_common_dur} days ({most_common_count} entities)\n"
            f"  Other spans      : {others}\n"
            f"  Proceeding with full grid (0 to {max_dur} days).\n"
            f"  Entities with shorter spans will appear inactive after their span ends."
        )

    return max_dur


def _build_relative_intervals(data: pd.DataFrame, entity_col: str) -> pd.DataFrame:
    """
    Parse pipe-delimited event_starts/event_ends into a long-form DataFrame
    of (entity, start_day, end_day) — day offsets relative to each entity's
    own span_start. All datetime arithmetic done upfront, everything
    downstream works in pure integers.

    Returns DataFrame with columns: [entity_col, start_day, end_day]
    Only entities with coverage are included.
    """
    covered = data[data["event_starts"].notna() & data["event_ends"].notna()].copy()
    if covered.empty:
        return pd.DataFrame(columns=[entity_col, "start_day", "end_day"])

    rows = []
    for _, row in covered.iterrows():
        # Normalize span_start to midnight — no time component
        span_start = pd.Timestamp(row["span_start"]).normalize()
        span_end   = pd.Timestamp(row["span_end"]).normalize()
        span_days  = (span_end - span_start).days

        starts_raw = str(row["event_starts"]).split(" | ")
        ends_raw   = str(row["event_ends"]).split(" | ")

        for s, e in zip(starts_raw, ends_raw):
            try:
                ev_start = pd.Timestamp(s.strip()).normalize()
                ev_end   = pd.Timestamp(e.strip()).normalize()
            except Exception:
                continue

            # Convert to day offsets, clip to [0, span_days]
            start_day = max(0,         (ev_start - span_start).days)
            end_day   = min(span_days, (ev_end   - span_start).days)

            if end_day > start_day:
                rows.append({
                    entity_col:  row[entity_col],
                    "start_day": start_day,
                    "end_day":   end_day,
                })

    return pd.DataFrame(rows)


def _active_at_day(intervals: pd.DataFrame, entity_col: str, day: int) -> set:
    """Return set of entities with an interval containing `day`."""
    if intervals.empty:
        return set()
    mask = (intervals["start_day"] <= day) & (intervals["end_day"] > day)
    return set(intervals.loc[mask, entity_col].unique())


# --------------------------------------------------------------------------- #
# Public API — activity over time
# --------------------------------------------------------------------------- #

def calc_activity_over_time(
    data: pd.DataFrame,
    entity_col: str,
    granularity: str = "month",
) -> pd.DataFrame:
    """
    Compute fraction of active entities at each relative day offset.

    X axis is days relative to each entity's own span_start (day 0 = span_start).
    At each step, counts how many entities have at least one active interval
    covering that day.

    Parameters
    ----------
    data : pd.DataFrame
        The intermediate DataFrame.
    entity_col : str
        Column identifying the entity.
    granularity : str
        Step size — "day" (every day), "week" (every 7 days),
        or "month" (every 30 days). Default "month".

    Returns
    -------
    pd.DataFrame
        Columns: [day, n_total, n_active, pct_active, n_entered, n_exited]
        pct_active is a fraction (0–1).
        First period has NA for n_entered and n_exited.
    """
    if granularity not in {"day", "week", "month"}:
        raise ValueError(
            f"{_ERROR_PREFIX}: granularity must be 'day', 'week', or 'month', "
            f"got '{granularity}'"
        )

    # --- Validate span durations ---
    max_dur_days = _validate_span_durations(data, entity_col)
    n_total      = len(data)

    # --- Step size ---
    step = {"day": 1, "week": 7, "month": 30}[granularity]

    # --- Build relative intervals (all datetime work done here) ---
    intervals = _build_relative_intervals(data, entity_col)

    # --- Day grid ---
    day_grid = list(range(0, max_dur_days + 1, step))

    # --- Compute active set per step ---
    rows = []
    prev_active: set | None = None

    for day in day_grid:
        active_set = _active_at_day(intervals, entity_col, day)
        n_active   = len(active_set)
        pct_active = round(n_active / n_total, 4) if n_total > 0 else 0.0

        if prev_active is None:
            n_entered = pd.NA
            n_exited  = pd.NA
        else:
            n_entered = len(active_set - prev_active)
            n_exited  = len(prev_active - active_set)

        rows.append({
            "day":       day,
            "n_total":   n_total,
            "n_active":  n_active,
            "pct_active": pct_active,
            "n_entered": n_entered,
            "n_exited":  n_exited,
        })

        prev_active = active_set

    return pd.DataFrame(rows).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Tier diagnostics
# --------------------------------------------------------------------------- #

def _pct(n: int, denom: int) -> float:
    return round(100 * n / denom, 1) if denom > 0 else 0.0


def _count_pct(n: int, denom: int) -> dict:
    return {"n": int(n), "pct": float(_pct(n, denom))}


def _stats(series: pd.Series, percentiles: list[int]) -> dict:
    clean = series.dropna()
    if clean.empty:
        return {"mean": None, **{f"p{p}": None for p in percentiles}}
    result = {"mean": round(float(clean.mean()), 1)}
    for p in percentiles:
        result[f"p{p}"] = round(float(np.percentile(clean, p)), 1)
    return result


def _covered(data: pd.DataFrame) -> pd.DataFrame:
    return data[data["active_days"].notna()].copy()


def calc_tier1(data: pd.DataFrame, entity_col: str) -> dict:
    total     = len(data)
    n_covered = int(data["active_days"].notna().sum())
    n_none    = total - n_covered
    return {
        "# denominator: total entities": None,
        "t1_total_entities": total,
        "t1_no_coverage":    _count_pct(n_none,    total),
        "t1_any_coverage":   _count_pct(n_covered, total),
    }


def calc_tier2(data: pd.DataFrame, entity_col: str) -> dict:
    cov       = _covered(data)
    n_covered = len(cov)
    if n_covered == 0:
        return {"# denominator: entities with any coverage": None,
                "t2_no_covered_entities": True}

    span   = cov["span_duration_days"]
    active = cov["active_days"]
    before = cov["inactive_days_before_first_event"]
    after  = cov["inactive_days_after_last_event"]
    middle = cov["inactive_days_middle"]

    full       = active >= span
    entered    = before > 0
    exited     = after  > 0
    has_middle = middle > 0

    return {
        "# denominator: entities with any coverage (t1_any_coverage)": None,
        "t2_full_coverage":                 _count_pct(int(full.sum()),                              n_covered),
        "t2_entered_during_span":           _count_pct(int(entered.sum()),                           n_covered),
        "t2_exited_during_span":            _count_pct(int(exited.sum()),                            n_covered),
        "t2_has_middle_gaps":               _count_pct(int(has_middle.sum()),                        n_covered),
        "t2_entered_late_and_exited_early": _count_pct(int((entered & exited).sum()),                n_covered),
        "t2_entered_late_and_has_gaps":     _count_pct(int((entered & has_middle).sum()),            n_covered),
        "t2_exited_early_and_has_gaps":     _count_pct(int((exited  & has_middle).sum()),            n_covered),
        "t2_clean_entry_exit_gaps_only":    _count_pct(int((~entered & ~exited & has_middle).sum()), n_covered),
    }


def calc_tier3(data: pd.DataFrame, entity_col: str, percentiles: list[int] = [25, 50, 75]) -> dict:
    cov        = _covered(data)
    before_pos = cov[cov["inactive_days_before_first_event"] > 0]
    after_pos  = cov[cov["inactive_days_after_last_event"]   > 0]
    middle_pos = cov[cov["inactive_days_middle"]             > 0]

    return {
        "# denominator: entities with any coverage unless noted": None,
        "t3_active_days":   _stats(cov["active_days"],   percentiles),
        "t3_inactive_days": _stats(cov["inactive_days"], percentiles),
        f"t3_inactive_days_before_first_event (n={len(before_pos)}, entities where before>0)":
            _stats(before_pos["inactive_days_before_first_event"], percentiles),
        f"t3_inactive_days_after_last_event (n={len(after_pos)}, entities where after>0)":
            _stats(after_pos["inactive_days_after_last_event"], percentiles),
        f"t3_inactive_days_middle (n={len(middle_pos)}, entities where middle>0)":
            _stats(middle_pos["inactive_days_middle"], percentiles),
    }


# --------------------------------------------------------------------------- #
# self_analyze workhorse
# --------------------------------------------------------------------------- #

def compute_from_pipe_delimited(
    data: pd.DataFrame,
    entity_col: str,
) -> pd.DataFrame:
    """
    Compute active/inactive day columns from pipe-delimited event columns.
    Called by PipeDelimitedIntermediateEvents.self_analyze().

    Requires columns: span_start, span_end, event_starts, event_ends.

    Returns the input DataFrame with added columns:
    span_duration_days, active_days, inactive_days,
    inactive_days_before_first_event, inactive_days_after_last_event,
    inactive_days_middle, first_event_start, last_event_end.
    """
    from .events_within_span_analyzer_utils import compute_activity_inactivity

    if "span_start" not in data.columns or "event_starts" not in data.columns:
        raise ValueError(
            "[compute_from_pipe_delimited] Error: data must have "
            "span_start, span_end, event_starts, event_ends columns"
        )

    # Explode pipe-delimited intervals into a long-form events DataFrame
    rows = []
    for _, row in data.iterrows():
        if pd.isna(row.get("event_starts")):
            continue
        starts = str(row["event_starts"]).split(" | ")
        ends   = str(row["event_ends"]).split(" | ")
        for s, e in zip(starts, ends):
            try:
                rows.append({
                    entity_col: row[entity_col],
                    "start":    pd.Timestamp(s.strip()),
                    "end":      pd.Timestamp(e.strip()),
                })
            except Exception:
                continue

    if not rows:
        # No events — all entities get NA analysis columns
        out = data.copy()
        for col in ["span_duration_days", "active_days", "inactive_days",
                    "inactive_days_before_first_event",
                    "inactive_days_after_last_event",
                    "inactive_days_middle", "first_event_start", "last_event_end"]:
            if col not in out.columns:
                out[col] = pd.NA
        return out

    events_df = pd.DataFrame(rows)
    spans_df  = data[[entity_col, "span_start", "span_end"]].copy()

    analysis = compute_activity_inactivity(
        events_df=events_df,
        span_df=spans_df,
        entity_col=entity_col,
        start_col="start",
        end_col="end",
        span_start_col="span_start",
        span_end_col="span_end",
    )

    # Analysis columns to add (drop span cols already in data)
    add_cols = ["span_duration_days", "active_days", "inactive_days",
                "inactive_days_before_first_event", "inactive_days_after_last_event",
                "inactive_days_middle", "first_event_start", "last_event_end"]

    out = data.copy()
    for col in add_cols:
        if col in analysis.columns:
            mapping = analysis.set_index(entity_col)[col]
            out[col] = out[entity_col].map(mapping)

    return out
