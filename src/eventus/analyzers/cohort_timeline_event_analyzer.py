"""
cohort_timeline_event_analyzer.py
CohortTimelineEventAnalyzer — event coverage analytics for one identity
within a CohortTimeline.
"""
from __future__ import annotations
import pandas as pd

from eventus.intermediates.cohort_timeline import CohortTimeline
from . import cohort_timeline_event_analyzer_utils as utils

_WARNING = "[CohortTimelineEventAnalyzer] Warning"
_ERROR = "[CohortTimelineEventAnalyzer] Error"


class CohortTimelineEventAnalyzer:
    """
    I compute event coverage analytics for one event identity within a CohortTimeline.

    Raises at construction if:
    - no obs period on the CohortTimeline
    - identity not in ct.event_identities
    - evt_{identity}_active_days already exists (already analyzed)
    """

    _ct: CohortTimeline
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

        # Prevent changes to original
        cohort_timeline_copy = cohort_timeline.copy() 

        # Initialize attributes
        self._ct       = cohort_timeline_copy
        self._identity = identity

    @property
    def identity(self) -> str:
        return self._identity

    def enrich_with_event_coverage(self) -> CohortTimeline:
        # Return the same cohort timeline object if that event identity was already enriched
        if utils.is_coverage_already_analyzed(self._identity, self._ct.data.columns.tolist()):
            print(f"{_WARNING} enrich_with_event_coverage was called but the analysis already existed")
            return self._ct

        enriched = utils.compute_coverage(self._ct.data, self._ct.entity_col, self._identity)
        new_object = CohortTimeline(enriched, self._ct.entity_col)
        self._ct = new_object
        return new_object

    def compute_activity_over_time(
        self,
        granularity: str = "month",
        mode:        str = "normalized",
    ):
        """
        Compute per-timepoint activity statistics.

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
        utils.require_coverage_exists(
            self._identity, self._ct.data.columns.tolist(), "compute_activity_over_time"
        )
        return utils.calc_activity_over_time(
            self._ct.data, self._ct.entity_col, self._identity, granularity, mode
        )

    def get_summary(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        utils.require_coverage_exists(
            self._identity, self._ct.data.columns.tolist(), "summary"
        )
        return {
            "tier1": utils.calc_tier1(self._ct.data, self._ct.entity_col, self._identity),
            "tier2": utils.calc_tier2(self._ct.data, self._ct.entity_col, self._identity),
            "tier3": utils.calc_tier3(self._ct.data, self._ct.entity_col, self._identity, percentiles),
        }

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"CohortTimelineEventAnalyzer(\n"
            f"  identity     : '{self._identity}'\n"
            f"  entities     : {len(self._ct):,}\n"
            f"  has_coverage : {utils.active_col(self._identity) in self._ct.data.columns}\n"
            f")"
        )
