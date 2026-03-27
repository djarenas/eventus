"""
span_analyzer_summary.py
Summary dataclass and builder for EventsWithinSpansAnalyzer results.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import yaml
import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Dataclass
# --------------------------------------------------------------------------- #

@dataclass
class EventsWithinSpansAnalyzerSummary:
    """
    Structured summary of compute_activity_inactivity output.

    Attributes
    ----------
    tier1 : dict
        Funnel — mutually exclusive, all percentages are out of total entities.
    tier2 : dict
        Behavioral flags — overlapping, all percentages are out of
        entities WITH any coverage (t1_any_coverage).
    tier3 : dict
        Continuous stats — computed only on entities with any coverage,
        with sub-breakdowns computed only on entities where the metric > 0.
    """
    tier1: dict
    tier2: dict
    tier3: dict

    def to_dict(self) -> dict:
        return {"tier1": self.tier1, "tier2": self.tier2, "tier3": self.tier3}

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def print_yaml(self) -> None:
        print(self.to_yaml())

    def __repr__(self) -> str:
        return self.to_yaml()


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #

def summarize(
    results_df: pd.DataFrame,
    *,
    percentiles: List[int] = [25, 50, 75],
) -> EventsWithinSpansAnalyzerSummary:
    """
    Build an EventsWithinSpansAnalyzerSummary from the output of
    compute_activity_inactivity.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of compute_activity_inactivity — one row per entity.
    percentiles : list of int
        Percentiles to compute for Tier 3 stats. Default: [25, 50, 75].

    Returns
    -------
    EventsWithinSpansAnalyzerSummary
    """
    _validate_results_df(results_df)

    total       = len(results_df)
    has_coverage = results_df["active_days"].notna()
    covered_df  = results_df[has_coverage].copy()
    n_covered   = len(covered_df)

    tier1 = _build_tier1(results_df, total, n_covered)
    tier2 = _build_tier2(covered_df, n_covered)
    tier3 = _build_tier3(covered_df, percentiles)

    return EventsWithinSpansAnalyzerSummary(tier1=tier1, tier2=tier2, tier3=tier3)


# --------------------------------------------------------------------------- #
# Internal builders
# --------------------------------------------------------------------------- #

def _pct(n: int, denom: int) -> float:
    """Round percentage to 1 decimal place."""
    if denom == 0:
        return 0.0
    return round(100 * n / denom, 1)

def _count_pct(n: int, denom: int) -> dict:
    return {"n": int(n), "pct": float(_pct(n, denom))}

def _stats(series: pd.Series, percentiles: List[int]) -> dict:
    """Compute mean, and requested percentiles for a numeric series."""
    clean = series.dropna()
    if clean.empty:
        return {"mean": None, **{f"p{p}": None for p in percentiles}}
    result = {"mean": round(float(clean.mean()), 1)}
    for p in percentiles:
        result[f"p{p}"] = round(float(np.percentile(clean, p)), 1)
    return result


def _build_tier1(df: pd.DataFrame, total: int, n_covered: int) -> dict:
    """
    Tier 1 — Funnel.
    Denominator for all percentages: total entities.
    """
    n_no_coverage = total - n_covered
    return {
        "# denominator: total entities in results_df": None,
        "t1_total_entities": total,
        "t1_no_coverage":    _count_pct(n_no_coverage, total),
        "t1_any_coverage":   _count_pct(n_covered,     total),
    }


def _build_tier2(covered_df: pd.DataFrame, n_covered: int) -> dict:
    """
    Tier 2 — Behavioral flags (overlapping).
    Denominator for all percentages: entities with any coverage (t1_any_coverage).
    """
    span_days  = covered_df["span_duration_days"]
    active     = covered_df["active_days"]
    before     = covered_df["inactive_days_before_first_event"]
    after      = covered_df["inactive_days_after_last_event"]
    middle     = covered_df["inactive_days_middle"]

    full        = (active >= span_days)
    entered     = (before > 0)
    exited      = (after  > 0)
    has_middle  = (middle > 0)

    entered_and_exited      = entered & exited
    entered_and_gaps        = entered & has_middle
    exited_and_gaps         = exited  & has_middle
    clean_entry_exit_gaps   = (~entered) & (~exited) & has_middle

    return {
        "# denominator: entities with any coverage (t1_any_coverage)": None,
        "t2_full_coverage":                  _count_pct(full.sum(),                   n_covered),
        "t2_entered_during_span":            _count_pct(entered.sum(),                n_covered),
        "t2_exited_during_span":             _count_pct(exited.sum(),                 n_covered),
        "t2_has_middle_gaps":                _count_pct(has_middle.sum(),             n_covered),
        "t2_entered_late_and_exited_early":  _count_pct(entered_and_exited.sum(),     n_covered),
        "t2_entered_late_and_has_gaps":      _count_pct(entered_and_gaps.sum(),       n_covered),
        "t2_exited_early_and_has_gaps":      _count_pct(exited_and_gaps.sum(),        n_covered),
        "t2_clean_entry_exit_gaps_only":     _count_pct(clean_entry_exit_gaps.sum(),  n_covered),
    }


def _build_tier3(covered_df: pd.DataFrame, percentiles: List[int]) -> dict:
    """
    Tier 3 — Continuous stats.
    All stats computed on entities with any coverage (t1_any_coverage).
    Sub-breakdowns (before/after/middle) computed only on entities where
    that metric > 0 — denominator noted per key.
    """
    before_pos = covered_df[covered_df["inactive_days_before_first_event"] > 0]
    after_pos  = covered_df[covered_df["inactive_days_after_last_event"]   > 0]
    middle_pos = covered_df[covered_df["inactive_days_middle"]             > 0]

    return {
        "# denominator: entities with any coverage unless noted": None,
        "t3_active_days": _stats(covered_df["active_days"],   percentiles),
        "t3_inactive_days": _stats(covered_df["inactive_days"], percentiles),
        f"t3_inactive_days_before_first_event (n={len(before_pos)}, entities where before>0)":
            _stats(before_pos["inactive_days_before_first_event"], percentiles),
        f"t3_inactive_days_after_last_event (n={len(after_pos)}, entities where after>0)":
            _stats(after_pos["inactive_days_after_last_event"], percentiles),
        f"t3_inactive_days_middle (n={len(middle_pos)}, entities where middle>0)":
            _stats(middle_pos["inactive_days_middle"], percentiles),
    }


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def _validate_results_df(df: pd.DataFrame) -> None:
    required = {
        "active_days", "inactive_days", "span_duration_days",
        "inactive_days_before_first_event",
        "inactive_days_after_last_event",
        "inactive_days_middle",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"[summarize] results_df is missing expected columns: {sorted(missing)}"
        )
