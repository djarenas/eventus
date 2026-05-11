"""
cohort_timeline_occurrence_analyzer.py
CohortTimelineOccurrenceAnalyzer — occurrence analysis for one identity
within a CohortTimeline.

Methods
-------
compute_volume()              → OccurrenceResultVolume
compute_timing(max_n)         → OccurrenceResultTiming
compute_shape()               → OccurrenceResultShape
compute_survival(ci_method)   → SurvivalResult

enrich_with_volume()          → CohortTimeline  (with occ_comp_{identity}_n)
enrich_with_timing(max_n)     → CohortTimeline  (with occ_comp_{identity}_time_to_*, recency_days)
enrich_with_shape()           → CohortTimeline  (with occ_comp_{identity}_mean_gap, ...)
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.occurrence_result_volume import OccurrenceResultVolume
from eventus.intermediates.occurrence_result_timing import OccurrenceResultTiming
from eventus.intermediates.occurrence_result_shape  import OccurrenceResultShape
from eventus.intermediates.survival_result          import SurvivalResult
import eventus.intermediates.survival_result_utils as survival_utils
import eventus.intermediates.cohort_timeline_utils  as ct_utils
from . import occurrence_stats_utils as stats_utils

_ERROR = "[CohortTimelineOccurrenceAnalyzer] Error"


class CohortTimelineOccurrenceAnalyzer:
    """
    I compute occurrence statistics for one occurrence identity within
    a CohortTimeline.

    compute_* methods return a typed result object.
    enrich_with_* methods return a new CohortTimeline enriched with
    occ_comp_{identity}_{stat} columns. Existing columns are overwritten.

    Raises at construction if:
    - cohort_timeline is not a CohortTimeline
    - identity is not a non-empty string
    - cohort_timeline has no observation period
    - identity not in cohort_timeline.occurrence_identities
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
                f"obs_start and obs_end are required to compute occurrence stats."
            )
        if identity not in cohort_timeline.occurrence_identities:
            raise ValueError(
                f"{_ERROR} identity '{identity}' not found in "
                f"occurrence_identities: {cohort_timeline.occurrence_identities}"
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
    # Shared setup
    # ------------------------------------------------------------------ #

    def _base_data(self) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Return the raw data and parsed obs period series.
        Called at the top of every compute/enrich method.
        """
        data      = self._ct.data
        obs_start = pd.to_datetime(data["obs_start"]).dt.normalize()
        obs_end   = pd.to_datetime(data["obs_end"]).dt.normalize()
        series    = data[f"occ_{self._identity}"]
        return data, series, obs_start, obs_end

    # ------------------------------------------------------------------ #
    # Private stat computation — shared by compute_* and enrich_with_*
    # ------------------------------------------------------------------ #

    def _compute_volume_stats(
        self,
        series:    pd.Series,
        obs_start: pd.Series,
        obs_end:   pd.Series,
    ) -> pd.DataFrame:
        return stats_utils.compute_volume_stats(series, obs_start, obs_end)

    def _compute_timing_stats(
        self,
        series:    pd.Series,
        obs_start: pd.Series,
        obs_end:   pd.Series,
        max_n:     int,
    ) -> pd.DataFrame:
        return stats_utils.compute_timing_stats(series, obs_start, obs_end, max_n)

    def _compute_shape_stats(
        self,
        series:    pd.Series,
        obs_start: pd.Series,
        obs_end:   pd.Series,
    ) -> pd.DataFrame:
        return stats_utils.compute_shape_stats(series, obs_start, obs_end)

    def _build_result_data(
        self,
        data:      pd.DataFrame,
        stats_df:  pd.DataFrame,
        obs_start: pd.Series,
        obs_end:   pd.Series,
    ) -> pd.DataFrame:
        """
        Assemble the result DataFrame:
        entity_col + obs_start + obs_end + computed stats.
        """
        result = data[[self._ct.entity_col]].copy()
        result["obs_start"] = obs_start.values
        result["obs_end"]   = obs_end.values
        for col in stats_df.columns:
            result[col] = stats_df[col].values
        return result

    # ------------------------------------------------------------------ #
    # compute_* — return typed result objects
    # ------------------------------------------------------------------ #

    def compute_volume(self) -> OccurrenceResultVolume:
        """
        Compute per-entity occurrence counts.

        Returns
        -------
        OccurrenceResultVolume
            One row per entity. Columns: obs_start, obs_end, n.
        """
        data, series, obs_start, obs_end = self._base_data()
        stats_df    = self._compute_volume_stats(series, obs_start, obs_end)
        result_data = self._build_result_data(data, stats_df, obs_start, obs_end)
        return OccurrenceResultVolume(result_data, self._ct.entity_col, self._identity)

    def compute_timing(self, max_n: int) -> OccurrenceResultTiming:
        """
        Compute per-entity timing of the nth occurrence and recency.

        Parameters
        ----------
        max_n : int
            Maximum nth occurrence to compute timing for. Must be >= 1.

        Returns
        -------
        OccurrenceResultTiming
            One row per entity. Columns: obs_start, obs_end,
            time_to_1 ... time_to_{max_n}, recency_days.
        """
        self._validate_max_n(max_n)
        data, series, obs_start, obs_end = self._base_data()
        stats_df    = self._compute_timing_stats(series, obs_start, obs_end, max_n)
        result_data = self._build_result_data(data, stats_df, obs_start, obs_end)
        return OccurrenceResultTiming(result_data, self._ct.entity_col, self._identity, max_n)

    def compute_shape(self) -> OccurrenceResultShape:
        """
        Compute per-entity behavioral fingerprint over the full date list.

        Returns
        -------
        OccurrenceResultShape
            One row per entity. Columns: obs_start, obs_end, mean_gap,
            std_gap, cv_gap, min_gap, max_gap, burstiness, memory,
            density, center_of_mass.
            NaN where minimum occurrence threshold is not met.
        """
        data, series, obs_start, obs_end = self._base_data()
        stats_df    = self._compute_shape_stats(series, obs_start, obs_end)
        result_data = self._build_result_data(data, stats_df, obs_start, obs_end)
        return OccurrenceResultShape(result_data, self._ct.entity_col, self._identity)

    # ------------------------------------------------------------------ #
    # enrich_with_* — return new CohortTimeline with occ_comp_ columns
    # ------------------------------------------------------------------ #

    def enrich_with_volume(self) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with occ_comp_{identity}_n.
        Overwrites the column if it already exists.
        """
        data, series, obs_start, obs_end = self._base_data()
        stats_df     = self._compute_volume_stats(series, obs_start, obs_end)
        enriched_df  = ct_utils.attach_occ_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    def enrich_with_timing(self, max_n: int) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with
        occ_comp_{identity}_time_to_1 ... time_to_{max_n} and recency_days.
        Overwrites columns if they already exist.

        Parameters
        ----------
        max_n : int
            Maximum nth occurrence to compute timing for. Must be >= 1.
        """
        self._validate_max_n(max_n)
        data, series, obs_start, obs_end = self._base_data()
        stats_df    = self._compute_timing_stats(series, obs_start, obs_end, max_n)
        enriched_df = ct_utils.attach_occ_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    def enrich_with_shape(self) -> CohortTimeline:
        """
        Return a new CohortTimeline enriched with occ_comp_{identity}_mean_gap,
        std_gap, cv_gap, min_gap, max_gap, burstiness, memory, density,
        center_of_mass. Overwrites columns if they already exist.
        """
        data, series, obs_start, obs_end = self._base_data()
        stats_df    = self._compute_shape_stats(series, obs_start, obs_end)
        enriched_df = ct_utils.attach_occ_comp_columns(data, stats_df, self._identity)
        return CohortTimeline(enriched_df, self._ct.entity_col)

    # ------------------------------------------------------------------ #
    # compute_survival — different geometry, always returns result object
    # ------------------------------------------------------------------ #

    def compute_survival(self, ci_method: str = "greenwood") -> SurvivalResult:
        """
        Compute a Kaplan-Meier survival curve for time to first occurrence.

        Entities with no occurrence are treated as right-censored at their
        obs_duration_days. Excluding them would silently bias the curve.

        Parameters
        ----------
        ci_method : str
            Confidence interval method. Currently only 'greenwood'.

        Returns
        -------
        SurvivalResult
            One row per unique event timepoint. Carries n_total,
            n_events_total, n_censored_total, and the KM table with
            CI bounds.
        """
        data, series, obs_start, obs_end = self._base_data()

        obs_duration  = (obs_end - obs_start).dt.days.values.astype(float)
        time_to_first = np.array([
            survival_utils._time_to_first(val, s, e)
            for val, s, e in zip(series, obs_start, obs_end)
        ], dtype=float)

        survival_table = survival_utils.compute_survival_table(
            time_to_event = time_to_first,
            obs_duration  = obs_duration,
            ci_method     = ci_method,
        )

        n_total    = len(time_to_first)
        n_events   = int(np.sum(~np.isnan(time_to_first)))
        n_censored = n_total - n_events

        return SurvivalResult(
            data             = survival_table,
            label            = self._identity,
            n_total          = n_total,
            n_events_total   = n_events,
            n_censored_total = n_censored,
            ci_method        = ci_method,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _validate_max_n(self, max_n: int) -> None:
        if not isinstance(max_n, int):
            raise TypeError(
                f"{_ERROR} max_n must be an integer, "
                f"got {type(max_n).__name__}"
            )
        if max_n < 1:
            raise ValueError(
                f"{_ERROR} max_n must be >= 1, got {max_n}"
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"CohortTimelineOccurrenceAnalyzer(\n"
            f"  identity  : '{self._identity}'\n"
            f"  entities  : {len(self._ct):,}\n"
            f")"
        )
