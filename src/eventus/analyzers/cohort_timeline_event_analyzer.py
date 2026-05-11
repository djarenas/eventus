"""
cohort_timeline_event_analyzer.py
CohortTimelineEventAnalyzer — event coverage analytics for one identity
within a CohortTimeline.

Methods
-------
enrich_with_event_coverage()              → CohortTimeline
compute_activity_over_time(granularity, mode) → EventActivityOverTime
get_summary(percentiles)                  → EventCoverageSummary
"""
from __future__ import annotations
import pandas as pd

from eventus.intermediates.cohort_timeline           import CohortTimeline
from eventus.intermediates.event_activity_over_time  import EventActivityOverTime
from eventus.intermediates.event_coverage_summary    import EventCoverageSummary
from . import cohort_timeline_event_analyzer_utils as utils

_ERROR = "[CohortTimelineEventAnalyzer] Error"


class CohortTimelineEventAnalyzer:
    """
    I compute event coverage analytics for one event identity within
    a CohortTimeline.

    enrich_with_event_coverage() returns a new CohortTimeline enriched
    with evt_comp_{identity}_* columns. Always overwrites existing columns.

    compute_activity_over_time() and get_summary() auto-enrich internally
    if coverage columns are not yet present — the caller does not need to
    call enrich_with_event_coverage() first.

    Raises at construction if:
    - cohort_timeline is not a CohortTimeline
    - identity is not a non-empty string
    - cohort_timeline has no observation period
    - identity not in cohort_timeline.event_identities
    """

    _ct:       CohortTimeline
    _identity: str

    def __init__(self, cohort_timeline: CohortTimeline, identity: str) -> None:
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR} cohort_timeline must be a CohortTimeline, "
                f"got {type(cohort_timeline).__name__}"
            )
        if not isinstance(identity, str) or not identity.strip():
            raise TypeError(
                f"{_ERROR} identity must be a non-empty string, "
                f"got {identity!r}"
            )

        utils.require_obs_period(cohort_timeline.has_obs_period)
        utils.require_identity_present(identity, cohort_timeline.event_identities)

        self._ct       = cohort_timeline
        self._identity = identity

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def cohort_timeline(self) -> CohortTimeline:
        return self._ct

    # ------------------------------------------------------------------ #
    # Internal lazy enrichment
    # ------------------------------------------------------------------ #

    def _ensure_coverage(self) -> None:
        """
        Enrich self._ct with coverage columns if not already present.
        This is lazy initialization — called internally by methods that
        require coverage columns as a precondition.
        """
        if not utils.is_coverage_computed(self._identity, self._ct.data.columns.tolist()):
            enriched    = utils.compute_coverage(self._ct.data, self._ct.entity_col, self._identity)
            self._ct    = CohortTimeline(enriched, self._ct.entity_col)

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def enrich_with_event_coverage(self) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with evt_comp_{identity}_*
        coverage columns. Always overwrites existing columns.

        Returns
        -------
        CohortTimeline
            New instance with coverage columns attached.
        """
        enriched = utils.compute_coverage(self._ct.data, self._ct.entity_col, self._identity)
        self._ct = CohortTimeline(enriched, self._ct.entity_col)
        return self._ct

    def compute_activity_over_time(
        self,
        granularity: str = "month",
        mode:        str = "normalized",
    ) -> EventActivityOverTime:
        """
        Compute per-timepoint activity statistics.
        Auto-enriches with coverage columns if not already present.

        Parameters
        ----------
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
        self._ensure_coverage()
        return utils.calc_activity_over_time(
            self._ct.data, self._ct.entity_col, self._identity, granularity, mode
        )

    def get_summary(self, percentiles: list[int] = [25, 50, 75]) -> EventCoverageSummary:
        """
        Compute a tiered coverage summary.
        Auto-enriches with coverage columns if not already present.

        Parameters
        ----------
        percentiles : list[int]
            Percentiles to compute for distribution stats. Default [25, 50, 75].

        Returns
        -------
        EventCoverageSummary
        """
        self._ensure_coverage()
        return utils.calc_summary(
            self._ct.data, self._ct.entity_col, self._identity, percentiles
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"CohortTimelineEventAnalyzer(\n"
            f"  identity        : '{self._identity}'\n"
            f"  entities        : {len(self._ct):,}\n"
            f"  has_coverage    : {utils.is_coverage_computed(self._identity, self._ct.data.columns.tolist())}\n"
            f")"
        )
