"""
pipe_delimited_intermediate_events.py
Child of PipeDelimitedIntermediate for events-within-span analysis results.
Produced by EventsWithinSpansAnalyzer.calc_active_vs_inactive().
"""
from __future__ import annotations
import pandas as pd
import yaml

from .pipe_delimited_intermediate import PipeDelimitedIntermediate

_ERROR_PREFIX = "[PipeDelimitedIntermediateEvents] Error"

_ANALYSIS_COLS = {
    "span_duration_days",
    "active_days",
    "inactive_days",
    "inactive_days_before_first_event",
    "inactive_days_after_last_event",
    "inactive_days_middle",
    "first_event_start",
    "last_event_end",
}


class PipeDelimitedIntermediateEvents(PipeDelimitedIntermediate):
    """
    Result of EventsWithinSpansAnalyzer.calc_active_vs_inactive().

    Inherits from PipeDelimitedIntermediate — carries the standard
    pipe-delimited columns plus event analysis metrics.

    One row per entity.

    Additional columns beyond PipeDelimitedIntermediate
    ---------------------------------------------------
    span_duration_days                  : float
    active_days                         : float | NA
    inactive_days                       : float | NA
    inactive_days_before_first_event    : float | NA
    inactive_days_after_last_event      : float | NA
    inactive_days_middle                : float | NA
    first_event_start                   : pd.Timestamp | NA
    last_event_end                      : pd.Timestamp | NA

    All day columns except span_duration_days are NA if the entity
    has no events overlapping their span.
    """

    def __init__(self, data: pd.DataFrame, entity_col: str = "entity_id") -> None:
        super().__init__(data, entity_col)

    @property
    def is_analyzed(self) -> bool:
        """True if all analysis columns are present."""
        return _ANALYSIS_COLS.issubset(set(self.data.columns))

    def _require_analyzed(self, method_name: str) -> None:
        """Raise clearly if analysis columns are missing."""
        if not self.is_analyzed:
            missing = sorted(_ANALYSIS_COLS - set(self.data.columns))
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires analysis columns "
                f"which are missing: {missing}. Call .self_analyze() first."
            )

    # ------------------------------------------------------------------ #
    # Classmethod override
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        entity_col: str = "entity_id",
    ) -> "PipeDelimitedIntermediateEvents":
        """Build from an existing DataFrame (e.g. reloaded from to_csv())."""
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Diagnostics — thin wrappers over utils
    # ------------------------------------------------------------------ #

    def self_analyze(self) -> "PipeDelimitedIntermediateEvents":
        """
        Compute active/inactive day columns from event_starts/event_ends
        and span_start/span_end. Returns a new enriched instance.

        Requires: span_start, span_end, event_starts, event_ends columns.

        Returns
        -------
        PipeDelimitedIntermediateEvents
            New instance with added columns:
            active_days, inactive_days, inactive_days_before_first_event,
            inactive_days_after_last_event, inactive_days_middle,
            span_duration_days, first_event_start, last_event_end.
        """
        from .pipe_delimited_intermediate_events_utils import compute_from_pipe_delimited
        enriched_df = compute_from_pipe_delimited(self.data, self.entity_col)
        return PipeDelimitedIntermediateEvents(enriched_df, self.entity_col)

    def tier1(self) -> dict:
        """Funnel — no coverage vs any coverage. Denominator: all entities."""
        self._require_analyzed("tier1")
        from .pipe_delimited_intermediate_events_utils import calc_tier1
        return calc_tier1(self.data, self.entity_col)

    def tier2(self) -> dict:
        """Behavioral flags. Denominator: entities with any coverage."""
        self._require_analyzed("tier2")
        from .pipe_delimited_intermediate_events_utils import calc_tier2
        return calc_tier2(self.data, self.entity_col)

    def tier3(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        """Continuous stats on active/inactive days."""
        self._require_analyzed("tier3")
        from .pipe_delimited_intermediate_events_utils import calc_tier3
        return calc_tier3(self.data, self.entity_col, percentiles)

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

    def activity_over_time(self, granularity: str = "month") -> pd.DataFrame:
        """
        Compute percentage of active entities at each time period.

        Parameters
        ----------
        granularity : str
            Time resolution — 'day', 'week', or 'month'. Default 'month'.

        Returns
        -------
        pd.DataFrame
            Columns: [date, n_total, n_active, pct_active, n_entered, n_exited]
        """
        from .pipe_delimited_intermediate_events_utils import calc_activity_over_time
        return calc_activity_over_time(self.data, self.entity_col, granularity)

    def _histogram_plotter(self, config_path: str):
        from .viz_histograms import EventAnalysisHistogramPlotter
        return EventAnalysisHistogramPlotter(config_path, self)

    def plot_active_days(self, config_path: str, path: str) -> None:
        """Histogram of active days for all covered entities."""
        self._histogram_plotter(config_path).plot_active_days(path)

    def plot_inactive_days(self, config_path: str, path: str) -> None:
        """Histogram of total inactive days for all covered entities."""
        self._histogram_plotter(config_path).plot_inactive_days(path)

    def plot_inactive_before(self, config_path: str, path: str) -> None:
        """Histogram of inactive days before first event (where > 0)."""
        self._histogram_plotter(config_path).plot_inactive_before(path)

    def plot_inactive_after(self, config_path: str, path: str) -> None:
        """Histogram of inactive days after last event (where > 0)."""
        self._histogram_plotter(config_path).plot_inactive_after(path)

    def plot_inactive_middle(self, config_path: str, path: str) -> None:
        """Histogram of inactive days in middle gaps (where > 0)."""
        self._histogram_plotter(config_path).plot_inactive_middle(path)

    def plot_violin(self, config_path: str, path: str) -> None:
        """Violin plot comparing all inactive metrics side by side."""
        self._histogram_plotter(config_path).plot_violin(path)

    def plot_activity_over_time(
        self,
        config_path: str,
        path: str,
        granularity: str = "month",
    ) -> None:
        """
        Compute and plot activity over time.

        Parameters
        ----------
        config_path : str
            Path to an activity_over_time_config.yaml file.
        path : str
            Output file path. Supports .png, .jpg, .jpeg.
        granularity : str
            Time resolution — 'day', 'week', or 'month'. Default 'month'.
        """
        from .viz_activity_over_time import ActivityOverTimePlotter
        ts = self.activity_over_time(granularity=granularity)
        ActivityOverTimePlotter(config_path=config_path, timeseries=ts).plot(path)

    # ------------------------------------------------------------------ #
    # Sorting
    # ------------------------------------------------------------------ #

    def sort(
        self,
        by: list[str],
        ascending: bool | list[bool] = True,
    ) -> "PipeDelimitedIntermediateEvents":
        """
        Sort entities by one or more columns and return a new instance.

        Parameters
        ----------
        by : list[str]
            Column names to sort by. Must exist in data.
        ascending : bool or list[bool]
            Sort direction. Default True.

        Returns
        -------
        PipeDelimitedIntermediateEvents
            A new sorted instance. Original is unchanged.
        """
        invalid = [c for c in by if c not in self.data.columns]
        if invalid:
            raise ValueError(
                f"{_ERROR_PREFIX} sort(): column(s) not found: {invalid}. "
                f"Available: {sorted(self.data.columns.tolist())}"
            )
        sorted_df = self.data.sort_values(
            by=by, ascending=ascending, na_position="last"
        ).reset_index(drop=True)
        return PipeDelimitedIntermediateEvents(sorted_df, self.entity_col)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        n_covered = int(self.data["active_days"].notna().sum())
        n_total   = len(self.data)
        return (
            f"PipeDelimitedIntermediateEvents(\n"
            f"  entities     : {n_total}\n"
            f"  with coverage: {n_covered}\n"
            f"  no coverage  : {n_total - n_covered}\n"
            f")"
        )
