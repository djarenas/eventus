"""
events_within_span_analyzer.py
High-level analytics for Events collections within user-supplied spans.
"""
from __future__ import annotations
from .events_within_span_analyzer_utils import compute_activity_inactivity
from .validation_utils import validate_shared_entity_col
from .pipe_delimited_intermediate_events import PipeDelimitedIntermediateEvents


class EventsWithinSpansAnalyzer:
    """
    Analyzer for an Events collection within user-supplied per-entity spans.

    Overlapping events are merged once at construction time so all analytics
    receive clean, non-overlapping data.

    Attributes
    ----------
    events : Events
        Merged (non-overlapping) events collection.
    spans : EventsPerEntity
        One row per entity defining their span window.
    entity_col : str
        Column used to identify entities across both events and spans.
    meaningful_gap : int
        Gaps between consecutive events <= this many days are bridged
        and treated as continuous active time. Default 0 (no bridging).

    Examples
    --------
    Basic usage:
        analyzer = EventsWithinSpansAnalyzer(events, spans)
        result   = analyzer.calc_active_vs_inactive()

    With a 7-day gap bridge:
        analyzer = EventsWithinSpansAnalyzer(events, spans, meaningful_gap=7)
        result   = analyzer.calc_active_vs_inactive()
    """

    _ERROR = "[EventsWithinSpansAnalyzer] Error"

    def __init__(
        self,
        events,
        spans,
        entity_col: str | None = None,
        *,
        meaningful_gap: int = 0,
    ) -> None:
        from .events import Events
        from .events_per_entity import EventsPerEntity

        # --- Validate types ---
        if not isinstance(events, Events):
            raise TypeError(f"{self._ERROR}: events must be an Events object")
        if not isinstance(spans, EventsPerEntity):
            raise TypeError(f"{self._ERROR}: spans must be an EventsPerEntity object")

        # --- Validate meaningful_gap ---
        if not isinstance(meaningful_gap, int) or meaningful_gap < 0:
            raise ValueError(
                f"{self._ERROR}: meaningful_gap must be a non-negative integer"
            )

        # --- Resolve entity_col ---
        if entity_col is None:
            entity_col = events.semantics.entity_id_col
        if not isinstance(entity_col, str):
            raise TypeError(f"{self._ERROR}: entity_col must be a string")
        if entity_col not in events.data.columns:
            raise ValueError(
                f"{self._ERROR}: entity_col '{entity_col}' not found in events.data"
            )
        if entity_col not in spans.data.columns:
            raise ValueError(
                f"{self._ERROR}: entity_col '{entity_col}' not found in spans.data"
            )

        # --- Check semantics are compatible ---
        validate_shared_entity_col(events, spans, label_a="events", label_b="spans")

        # --- Merge overlapping events once, bridging small gaps ---
        self.events         = events.merge_overlapping_events(meaningful_gap=meaningful_gap)
        self.spans          = spans
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
        return self.spans.semantics.start_time_col

    @property
    def _span_end_col(self) -> str:
        return self.spans.semantics.end_time_col

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #

    def calc_active_vs_inactive(self) -> PipeDelimitedIntermediateEvents:
        """
        Compute active vs. inactive days for each entity within their span.

        Gaps between consecutive events <= meaningful_gap days are bridged
        and treated as active before any calculations are performed.

        Returns
        -------
        PipeDelimitedIntermediateEvents
            One row per entity. Inherits from PipeDelimitedIntermediate so
            it can be passed directly to StackedEventsPlotter and other
            visualization classes.
        """
        df = compute_activity_inactivity(
            events_df=self.events.data,
            span_df=self.spans.data,
            entity_col=self.entity_col,
            start_col=self._start_col,
            end_col=self._end_col,
            span_start_col=self._span_start_col,
            span_end_col=self._span_end_col,
        )
        return PipeDelimitedIntermediateEvents(df, self.entity_col)

    # ------------------------------------------------------------------ #
    # Special methods
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventsWithinSpansAnalyzer(\n"
            f"  events        : {self.events}\n"
            f"  spans         : {self.spans}\n"
            f"  entity_col    : '{self.entity_col}'\n"
            f"  meaningful_gap: {self.meaningful_gap} days\n"
            f")"
        )
