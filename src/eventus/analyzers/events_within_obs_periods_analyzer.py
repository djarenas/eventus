"""
events_within_obs_periods_analyzer.py
Analyzes Events within per-entity observation periods.
Produces PipeDelimitedIntermediateEvents.
"""
from __future__ import annotations
import sys
import pandas as pd

from .events_within_obs_period_analyzer_utils import compute_activity_inactivity
from .validation_utils import validate_shared_entity_col
from eventus.pipe_delimited_format.pipe_delimited_format_events import PipeDelimitedFormatEvents

_ERROR = "[EventsWithinObsPeriodsAnalyzer] Error"


class EventsWithinObsPeriodsAnalyzer:
    """
    Analyzer for an Events collection within per-entity observation periods.

    Overlapping events are merged once at construction time so all analytics
    receive clean, non-overlapping data.

    Parameters
    ----------
    events : Events
        A validated Events object.
    obs_period : ObsPeriodPerEntity
        One row per entity defining their observation window.
    entity_col : str | None
        Entity identifier column. Defaults to events.semantics.entity_id_col.
    meaningful_gap : int
        Gaps between consecutive events <= this many days are bridged
        and treated as continuous active time. Default 0.

    Examples
    --------
    >>> analyzer = EventsWithinObsPeriodsAnalyzer(events, obs_period)
    >>> result   = analyzer.calc_active_vs_inactive()

    >>> analyzer = EventsWithinObsPeriodsAnalyzer(
    ...     events, obs_period, meaningful_gap=7
    ... )
    """

    def __init__(
        self,
        events,
        obs_period,
        entity_col:     str | None = None,
        *,
        meaningful_gap: int = 0,
    ) -> None:
        from eventus.data_objects.events import Events
        from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity
        from eventus.data_objects.events_utils import merge_overlapping_events as _merge

        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR}: events must be an Events object, "
                f"got {type(events).__name__}"
            )
        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERROR}: obs_period must be an ObsPeriodPerEntity object, "
                f"got {type(obs_period).__name__}. "
                f"Use ObsPeriodPerEntity.from_calendar(), .from_age_window(), "
                f".from_events(), or EventsPerEntity.as_obs_period() to build one."
            )
        if not isinstance(meaningful_gap, int) or meaningful_gap < 0:
            raise ValueError(
                f"{_ERROR}: meaningful_gap must be a non-negative integer, "
                f"got {meaningful_gap!r}"
            )

        if entity_col is None:
            entity_col = events.semantics.entity_id_col
        if not isinstance(entity_col, str):
            raise TypeError(f"{_ERROR}: entity_col must be a string")
        if entity_col not in events.data.columns:
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' not found in events.data"
            )
        if entity_col not in obs_period.data.columns:
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' not found in obs_period.data"
            )

        validate_shared_entity_col(
            events, obs_period,
            label_a="events", label_b="obs_period"
        )

    
        merged_data = _merge(events.data, events.semantics, meaningful_gap)
        # Build a new Events from the merged data
        self.events         = Events(merged_data, events.semantics)
        self.obs_period     = obs_period
        self.entity_col     = entity_col
        self.meaningful_gap = meaningful_gap

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def _start_col(self) -> str:
        return self.events.semantics.start_time_col

    @property
    def _end_col(self) -> str:
        return self.events.semantics.end_time_col

    @property
    def _span_start_col(self) -> str:
        return self.obs_period.semantics.start_time_col

    @property
    def _span_end_col(self) -> str:
        return self.obs_period.semantics.end_time_col

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #

    def compute_event_coverage(self) -> PipeDelimitedFormatEvents:
        """
        Compute active vs. inactive days for each entity within their
        observation period.
 
        Returns
        -------
        PipeDelimitedIntermediateEvents
            One row per entity with pipe-delimited event dates and
            span boundaries.
        """
        df = compute_activity_inactivity(
            events_df      = self.events.data,
            span_df        = self.obs_period.data,
            entity_col     = self.entity_col,
            start_col      = self._start_col,
            end_col        = self._end_col,
            span_start_col = self._span_start_col,
            span_end_col   = self._span_end_col,
        )
        return PipeDelimitedFormatEvents(df, self.entity_col)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventsWithinObsPeriodsAnalyzer(\n"
            f"  events         : {len(self.events):,} rows\n"
            f"  obs_period     : {len(self.obs_period):,} entities "
            f"(identity='{self.obs_period.identity}')\n"
            f"  entity_col     : '{self.entity_col}'\n"
            f"  meaningful_gap : {self.meaningful_gap} days\n"
            f")"
        )
