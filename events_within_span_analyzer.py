"""
span_analyzer.py
High-level analytics for Events collections within user-supplied spans.
"""
from __future__ import annotations
from .span_analyzer_utils import compute_activity_inactivity
from .span_coverage_result import SpanCoverageResult


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
        One row per entity defining their span window. Must use the same
        entity_id_col as events, and must have start_time_col <= end_time_col.
    entity_col : str
        Column used to identify entities across both events and spans.
    meaningful_gap : int
        Gaps between consecutive events <= this many days are bridged
        and treated as continuous active time. Default 0 (no bridging).

    Examples
    --------
    Insurance coverage:
        analyzer = EventsWithinSpansAnalyzer(events, spans)
        results  = analyzer.calc_active_vs_inactive()

    With a 7-day fudge factor:
        analyzer = EventsWithinSpansAnalyzer(events, spans, meaningful_gap=7)
        results  = analyzer.calc_active_vs_inactive()
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
        """
        Parameters
        ----------
        events : Events
            A validated Events object — many rows per entity allowed.
        spans : EventsPerEntity
            A validated EventsPerEntity object — exactly one row per entity,
            where start_time_col is the span start and end_time_col is the
            span end.
        entity_col : str | None
            Column identifying the entity in both objects. Defaults to
            events.semantics.entity_id_col if not provided.
        meaningful_gap : int
            Gaps between consecutive events <= this many days are treated
            as continuous coverage. Default 0 (no bridging).
        """
        from .events import Events
        from .events_per_entity import EventsPerEntity

        # --- Validate types ---
        if not isinstance(events, Events):
            raise TypeError(f"{self._ERROR}: events must be an Events object")
        if not isinstance(spans, EventsPerEntity):
            raise TypeError(f"{self._ERROR}: spans must be an EventsPerEntity object")

        # --- Validate meaningful_gap ---
        if not isinstance(meaningful_gap, int) or meaningful_gap < 0:
            raise ValueError(f"{self._ERROR}: meaningful_gap must be a non-negative integer")

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
        if events.semantics.entity_id_col != spans.semantics.entity_id_col:
            raise ValueError(
                f"{self._ERROR}: events and spans have different entity_id_col — "
                f"'{events.semantics.entity_id_col}' vs '{spans.semantics.entity_id_col}'"
            )

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

    def calc_active_vs_inactive(self) -> SpanCoverageResult:
        """
        Compute active vs. inactive days for each entity within their span.

        Gaps between consecutive events <= meaningful_gap days are bridged
        and treated as active before any calculations are performed.

        Returns
        -------
        pd.DataFrame
            One row per entity with columns:
            [entity_col, span_start, span_end, span_duration_days,
             active_days, inactive_days,
             inactive_days_before_first_event,
             inactive_days_after_last_event,
             inactive_days_middle,
             first_event_start, last_event_end]

            All day columns except span_duration_days are NA if the entity
            has no events overlapping their span.
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
        return SpanCoverageResult(df, self.entity_col)

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