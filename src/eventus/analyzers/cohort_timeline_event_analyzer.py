"""
cohort_timeline_event_analyzer.py
CohortTimelineEventAnalyzer — event analysis for one identity
within a CohortTimeline.

Methods
-------
compute_volume()              → EventResultVolume
compute_timing(max_n)         → EventResultTiming
compute_shape()               → EventResultShape
compute_survival(ci_method)   → SurvivalResult

enrich_with_volume()          → CohortTimeline  (with evt_comp_{identity}_n)
enrich_with_timing(max_n)     → CohortTimeline  (with evt_comp_{identity}_time_to_*, recency_days)
enrich_with_shape()           → CohortTimeline  (with evt_comp_{identity}_mean_gap, ...)
"""
from __future__ import annotations
import numpy as np

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.event_result_volume import EventResultVolume
from eventus.intermediates.event_result_timing import EventResultTiming
from eventus.intermediates.event_result_shape  import EventResultShape
from eventus.intermediates.survival_result     import SurvivalResult
import eventus.intermediates.survival_result_utils as survival_utils
import eventus.intermediates.cohort_timeline_utils  as ct_utils
from . import event_stats_utils as stats_utils
from . import cohort_timeline_event_analyzer_utils as analyzer_utils

_ERROR = "[CohortTimelineEventAnalyzer] Error"


class CohortTimelineEventAnalyzer:
    """
    I compute event statistics for one event identity within
    a CohortTimeline.

    compute_* methods return a typed result object.
    enrich_with_* methods return a new CohortTimeline enriched with
    evt_comp_{identity}_{stat} columns. Existing columns are overwritten.

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
        if not cohort_timeline.has_obs_period:
            raise ValueError(
                f"{_ERROR} CohortTimeline has no observation period. "
                f"obs_start and obs_end are required to compute event stats."
            )
        if identity not in cohort_timeline.event_identities:
            raise ValueError(
                f"{_ERROR} identity '{identity}' not found in "
                f"event_identities: {cohort_timeline.event_identities}"
            )

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
    # compute_* — return typed result objects
    # ------------------------------------------------------------------ #

    def compute_volume(self) -> EventResultVolume:
        """
        Compute per-entity event counts.

        Returns
        -------
        EventResultVolume
            One row per entity. Columns: obs_start, obs_end, n.
        """
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_volume_stats(series, obs_start, obs_end)
        result_data = analyzer_utils.build_result_data(self._ct, data, stats_df, obs_start, obs_end)
        return EventResultVolume(result_data, self._ct.entity_col, self._identity)

    def compute_timing(self, max_n: int) -> EventResultTiming:
        """
        Compute per-entity timing of the nth event and recency.

        Parameters
        ----------
        max_n : int
            Maximum nth event to compute timing for. Must be >= 1.

        Returns
        -------
        EventResultTiming
            One row per entity. Columns: obs_start, obs_end,
            time_to_1 ... time_to_{max_n}, recency_days.
        """
        analyzer_utils.validate_max_n(max_n)
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_timing_stats(series, obs_start, obs_end, max_n)
        result_data = analyzer_utils.build_result_data(self._ct, data, stats_df, obs_start, obs_end)
        return EventResultTiming(result_data, self._ct.entity_col, self._identity, max_n)

    def compute_shape(self) -> EventResultShape:
        """
        Compute per-entity behavioral fingerprint over the full date list.

        Returns
        -------
        EventResultShape
            One row per entity. Columns: obs_start, obs_end, mean_gap,
            std_gap, cv_gap, min_gap, max_gap, burstiness, memory,
            density, center_of_mass.
            NaN where minimum event threshold is not met.
        """
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_shape_stats(series, obs_start, obs_end)
        result_data = analyzer_utils.build_result_data(self._ct, data, stats_df, obs_start, obs_end)
        return EventResultShape(result_data, self._ct.entity_col, self._identity)

    # ------------------------------------------------------------------ #
    # enrich_with_* — return new CohortTimeline with evt_comp_ columns
    # ------------------------------------------------------------------ #

    def enrich_with_volume(self) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with evt_comp_{identity}_n.
        Overwrites the column if it already exists.
        """
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_volume_stats(series, obs_start, obs_end)
        enriched_df = ct_utils.attach_evt_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    def enrich_with_timing(self, max_n: int) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with
        evt_comp_{identity}_time_to_1 ... time_to_{max_n} and recency_days.
        Overwrites columns if they already exist.

        Parameters
        ----------
        max_n : int
            Maximum nth event to compute timing for. Must be >= 1.
        """
        analyzer_utils.validate_max_n(max_n)
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_timing_stats(series, obs_start, obs_end, max_n)
        enriched_df = ct_utils.attach_evt_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    def enrich_with_shape(self) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with evt_comp_{identity}_mean_gap,
        std_gap, cv_gap, min_gap, max_gap, burstiness, memory, density,
        center_of_mass. Overwrites columns if they already exist.
        """
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        stats_df    = stats_utils.compute_shape_stats(series, obs_start, obs_end)
        enriched_df = ct_utils.attach_evt_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    # ------------------------------------------------------------------ #
    # compute_survival — different geometry, always returns result object
    # ------------------------------------------------------------------ #

    def compute_survival(self, ci_method: str = "greenwood") -> SurvivalResult:
        """
        Compute a Kaplan-Meier survival curve for time to first event.

        Entities with no event are treated as right-censored at their
        obs_duration_days. Excluding them would silently bias the curve.

        Parameters
        ----------
        ci_method : str
            Confidence interval method. Currently only 'greenwood'.

        Returns
        -------
        SurvivalResult
            One row per unique episode timepoint. Carries n_total,
            n_episodes_total, n_censored_total, and the KM table with
            CI bounds.
        """
        data, series, obs_start, obs_end = analyzer_utils.base_data(self._ct, self._identity)
        obs_duration, time_to_first = analyzer_utils.build_survival_arrays(series, obs_start, obs_end)

        survival_table = survival_utils.compute_survival_table(
            time_to_episode = time_to_first,
            obs_duration    = obs_duration,
            ci_method       = ci_method,
        )

        n_total    = len(time_to_first)
        n_episodes = int(np.sum(~np.isnan(time_to_first)))
        n_censored = n_total - n_episodes

        return SurvivalResult(
            data             = survival_table,
            label            = self._identity,
            n_total          = n_total,
            n_episodes_total = n_episodes,
            n_censored_total = n_censored,
            ci_method        = ci_method,
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"CohortTimelineEventAnalyzer(\n"
            f"  identity  : '{self._identity}'\n"
            f"  entities  : {len(self._ct):,}\n"
            f")"
        )
