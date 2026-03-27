"""
span_coverage_result.py
Result class returned by EventsWithinSpansAnalyzer.calc_active_vs_inactive().
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import yaml

_ERROR_PREFIX = "[SpanCoverageResult] Error"

_REQUIRED_COLS = {
    "span_start", "span_end", "span_duration_days",
    "active_days", "inactive_days",
    "inactive_days_before_first_event",
    "inactive_days_after_last_event",
    "inactive_days_middle",
    "first_event_start", "last_event_end",
    "event_starts", "event_ends",
}


class SpanCoverageResult:
    """
    Result of EventsWithinSpansAnalyzer.calc_active_vs_inactive().

    Wraps the results DataFrame and provides diagnostics, summaries,
    visualizations and export methods.

    Attributes
    ----------
    data : pd.DataFrame
        One row per entity with all coverage metrics.
    entity_col : str
        Column identifying the entity.
    """
    data: pd.DataFrame
    entity_col: str

    def __init__(self, data: pd.DataFrame, entity_col: str) -> None:
        self._validate(data, entity_col)
        self.data       = data.reset_index(drop=True)
        self.entity_col = entity_col

    # ------------------------------------------------------------------ #
    # Constructor
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(cls, data: pd.DataFrame, entity_col: str) -> "SpanCoverageResult":
        """
        Build a SpanCoverageResult directly from a DataFrame.

        Useful for reloading previously saved results (e.g. from to_csv()).

        Parameters
        ----------
        data : pd.DataFrame
            Must contain all required columns produced by
            compute_activity_inactivity.
        entity_col : str
            Column identifying the entity.

        Returns
        -------
        SpanCoverageResult
        """
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate(self, data: pd.DataFrame, entity_col: str) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"{_ERROR_PREFIX}: data must be a DataFrame")
        if not isinstance(entity_col, str):
            raise TypeError(f"{_ERROR_PREFIX}: entity_col must be a string")
        missing = _REQUIRED_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: data is missing required columns: {sorted(missing)}"
            )
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR_PREFIX}: entity_col '{entity_col}' not found in data"
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        n_covered   = self.data["active_days"].notna().sum()
        n_total     = len(self.data)
        return (
            f"SpanCoverageResult(\n"
            f"  entities    : {n_total}\n"
            f"  with coverage: {n_covered}\n"
            f"  no coverage : {n_total - n_covered}\n"
            f")"
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _pct(self, n: int, denom: int) -> float:
        return round(100 * n / denom, 1) if denom > 0 else 0.0

    def _count_pct(self, n: int, denom: int) -> dict:
        return {"n": int(n), "pct": float(self._pct(n, denom))}

    def _stats(self, series: pd.Series, percentiles: list[int]) -> dict:
        clean = series.dropna()
        if clean.empty:
            return {"mean": None, **{f"p{p}": None for p in percentiles}}
        result = {"mean": round(float(clean.mean()), 1)}
        for p in percentiles:
            result[f"p{p}"] = round(float(np.percentile(clean, p)), 1)
        return result

    @property
    def _covered(self) -> pd.DataFrame:
        """Entities with any coverage."""
        return self.data[self.data["active_days"].notna()].copy()

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def tier1(self) -> dict:
        """
        Funnel — mutually exclusive, adds to 100%.
        Denominator: total entities.
        """
        total     = len(self.data)
        n_covered = int(self.data["active_days"].notna().sum())
        n_none    = total - n_covered
        return {
            "# denominator: total entities": None,
            "t1_total_entities": total,
            "t1_no_coverage":    self._count_pct(n_none,    total),
            "t1_any_coverage":   self._count_pct(n_covered, total),
        }

    def tier2(self) -> dict:
        """
        Behavioral flags — overlapping.
        Denominator: entities with any coverage.
        """
        cov       = self._covered
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
            "t2_full_coverage":                 self._count_pct(int(full.sum()),                          n_covered),
            "t2_entered_during_span":           self._count_pct(int(entered.sum()),                       n_covered),
            "t2_exited_during_span":            self._count_pct(int(exited.sum()),                        n_covered),
            "t2_has_middle_gaps":               self._count_pct(int(has_middle.sum()),                    n_covered),
            "t2_entered_late_and_exited_early": self._count_pct(int((entered & exited).sum()),            n_covered),
            "t2_entered_late_and_has_gaps":     self._count_pct(int((entered & has_middle).sum()),        n_covered),
            "t2_exited_early_and_has_gaps":     self._count_pct(int((exited  & has_middle).sum()),        n_covered),
            "t2_clean_entry_exit_gaps_only":    self._count_pct(int((~entered & ~exited & has_middle).sum()), n_covered),
        }

    def tier3(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        """
        Continuous stats.
        All stats on entities with any coverage unless noted.
        Sub-breakdowns computed only on entities where that metric > 0.
        """
        cov        = self._covered
        before_pos = cov[cov["inactive_days_before_first_event"] > 0]
        after_pos  = cov[cov["inactive_days_after_last_event"]   > 0]
        middle_pos = cov[cov["inactive_days_middle"]             > 0]

        return {
            "# denominator: entities with any coverage unless noted": None,
            "t3_active_days":   self._stats(cov["active_days"],   percentiles),
            "t3_inactive_days": self._stats(cov["inactive_days"], percentiles),
            f"t3_inactive_days_before_first_event (n={len(before_pos)}, entities where before>0)":
                self._stats(before_pos["inactive_days_before_first_event"], percentiles),
            f"t3_inactive_days_after_last_event (n={len(after_pos)}, entities where after>0)":
                self._stats(after_pos["inactive_days_after_last_event"], percentiles),
            f"t3_inactive_days_middle (n={len(middle_pos)}, entities where middle>0)":
                self._stats(middle_pos["inactive_days_middle"], percentiles),
        }

    def full_summary(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        """All three tiers combined."""
        return {
            "tier1": self.tier1(),
            "tier2": self.tier2(),
            "tier3": self.tier3(percentiles),
        }

    def print_summary(self, percentiles: list[int] = [25, 50, 75]) -> None:
        """Print full summary as YAML to stdout."""
        print(yaml.dump(self.full_summary(percentiles), sort_keys=False, allow_unicode=True))

    def save_summary(self, path: str, percentiles: list[int] = [25, 50, 75]) -> None:
        """Write full summary as YAML to file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.full_summary(percentiles), f, sort_keys=False, allow_unicode=True)
        print(f"Summary saved to: {path}")

    # ------------------------------------------------------------------ #
    # Visualizations
    # ------------------------------------------------------------------ #

    def plot_stacked_bar(
        self,
        path: str,
        n_sample: int | None = None,
        random_state: int | None = None,
    ) -> None:
        """Per-entity stacked bar chart. Saves to path (.html/.png/.jpg/.jpeg)."""
        from .viz_helpers import plot_stacked_bar
        plot_stacked_bar(
            self.data, path, self.entity_col,
            n_sample=n_sample, random_state=random_state,
        )

    def plot_active_timeseries(self, path: str) -> None:
        """% of entities active per relative day. Saves to path."""
        from .viz_helpers import plot_active_timeseries
        plot_active_timeseries(self.data, path, self.entity_col)

    def plot_coverage_histogram(self, path: str) -> None:
        """Distribution of active_days. Saves to path."""
        from .viz_helpers import plot_coverage_histogram
        plot_coverage_histogram(self.data, path, self.entity_col)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def to_csv(self, path: str) -> None:
        """Save results DataFrame to CSV."""
        self.data.to_csv(path, index=False)
        print(f"Saved: {path}")