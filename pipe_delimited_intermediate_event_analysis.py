"""
pipe_delimited_intermediate_event_analysis.py
Child of PipeDelimitedIntermediate for events-within-span analysis results.
Produced by EventsWithinSpansAnalyzer.calc_active_vs_inactive().
"""
from __future__ import annotations
import pandas as pd
import yaml

from .pipe_delimited_intermediate import PipeDelimitedIntermediate

_ERROR_PREFIX = "[PipeDelimitedIntermediateEventAnalysis] Error"

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


class PipeDelimitedIntermediateEventAnalysis(PipeDelimitedIntermediate):
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
        self._validate_analysis_cols()

    def _validate_analysis_cols(self) -> None:
        missing = _ANALYSIS_COLS - set(self.data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: data is missing required analysis columns: "
                f"{sorted(missing)}"
            )

    # ------------------------------------------------------------------ #
    # Classmethod override
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        entity_col: str = "entity_id",
    ) -> "PipeDelimitedIntermediateEventAnalysis":
        """Build from an existing DataFrame (e.g. reloaded from to_csv())."""
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Diagnostics — thin wrappers over utils
    # ------------------------------------------------------------------ #

    def tier1(self) -> dict:
        """Funnel — no coverage vs any coverage. Denominator: all entities."""
        from .pipe_delimited_intermediate_event_analysis_utils import calc_tier1
        return calc_tier1(self.data, self.entity_col)

    def tier2(self) -> dict:
        """Behavioral flags. Denominator: entities with any coverage."""
        from .pipe_delimited_intermediate_event_analysis_utils import calc_tier2
        return calc_tier2(self.data, self.entity_col)

    def tier3(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        """Continuous stats on active/inactive days."""
        from .pipe_delimited_intermediate_event_analysis_utils import calc_tier3
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
        from .pipe_delimited_intermediate_event_analysis_utils import calc_activity_over_time
        return calc_activity_over_time(self.data, self.entity_col, granularity)

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
    ) -> "PipeDelimitedIntermediateEventAnalysis":
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
        PipeDelimitedIntermediateEventAnalysis
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
        return PipeDelimitedIntermediateEventAnalysis(sorted_df, self.entity_col)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        n_covered = int(self.data["active_days"].notna().sum())
        n_total   = len(self.data)
        return (
            f"PipeDelimitedIntermediateEventAnalysis(\n"
            f"  entities     : {n_total}\n"
            f"  with coverage: {n_covered}\n"
            f"  no coverage  : {n_total - n_covered}\n"
            f")"
        )
