"""
cohort_timeline_occurrence_analyzer.py
CohortTimelineOccurrenceAnalyzer — occurrence analysis for one identity
within a CohortTimeline.

Produces
--------
compute_volume()        → OccurrenceResultVolume
compute_timing(max_n)   → OccurrenceResultTiming
compute_shape()         → OccurrenceResultShape
compute_survival()      → SurvivalResult
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.occurrence_result_volume          import OccurrenceResultVolume
from eventus.intermediates.occurrence_result_timing          import OccurrenceResultTiming
from eventus.intermediates.occurrence_result_shape           import OccurrenceResultShape
from eventus.intermediates.survival_result                   import SurvivalResult
import eventus.intermediates.survival_result_utils as survival_utils
from . import occurrence_stats_utils as stats_utils

_ERROR = "[CohortTimelineOccurrenceAnalyzer] Error"


class CohortTimelineOccurrenceAnalyzer:
    """
    I compute occurrence statistics for one occurrence identity within
    a CohortTimeline.

    Each compute method is independently callable in any order.
    No state is mutated on the CohortTimeline.

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

    # ------------------------------------------------------------------ #
    # Shared setup
    # ------------------------------------------------------------------ #

    def _base_data(self) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Return the raw data and parsed obs period series.
        Called at the top of every compute method.
        """
        data      = self._ct.data
        obs_start = pd.to_datetime(data["obs_start"]).dt.normalize()
        obs_end   = pd.to_datetime(data["obs_end"]).dt.normalize()
        series    = data[f"occ_{self._identity}"]
        return data, series, obs_start, obs_end

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
    # Compute methods
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
        stats_df    = stats_utils.compute_volume_stats(series, obs_start, obs_end)
        result_data = self._build_result_data(data, stats_df, obs_start, obs_end)
        return OccurrenceResultVolume(result_data, self._ct.entity_col, self._identity)

    def compute_timing(self, max_n: int) -> OccurrenceResultTiming:
        """
        Compute per-entity timing of the nth occurrence and recency.

        Parameters
        ----------
        max_n : int
            Maximum nth occurrence to compute timing for.
            Must be a positive integer >= 1.

        Returns
        -------
        OccurrenceResultTiming
            One row per entity.
            Columns: obs_start, obs_end, time_to_1, ..., time_to_{max_n},
            recency_days.

        Raises
        ------
        TypeError  if max_n is not an integer.
        ValueError if max_n < 1.
        """
        if not isinstance(max_n, int):
            raise TypeError(
                f"{_ERROR} max_n must be an integer, "
                f"got {type(max_n).__name__}"
            )
        if max_n < 1:
            raise ValueError(
                f"{_ERROR} max_n must be >= 1, got {max_n}"
            )

        data, series, obs_start, obs_end = self._base_data()
        stats_df    = stats_utils.compute_timing_stats(series, obs_start, obs_end, max_n)
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
        stats_df    = stats_utils.compute_shape_stats(series, obs_start, obs_end)
        result_data = self._build_result_data(data, stats_df, obs_start, obs_end)
        return OccurrenceResultShape(result_data, self._ct.entity_col, self._identity)

    def compute_survival(self, ci_method: str = "greenwood") -> SurvivalResult:
        """
        Compute a Kaplan-Meier survival curve for time to first occurrence.

        Entities with no occurrence are treated as right-censored at their
        obs_duration_days — they are included in the risk set and correctly
        reduce the KM estimate. Excluding them would silently bias the curve.

        The x-axis is always normalized (day 0 = obs_start per entity).
        Calendar-mode survival curves are not supported — observation periods
        may differ across entities.

        Parameters
        ----------
        ci_method : str
            Confidence interval method. Currently only 'greenwood'.
            Default 'greenwood'.

        Returns
        -------
        SurvivalResult
            One row per unique event timepoint. Carries n_total,
            n_events_total, n_censored_total, and the KM table with
            CI bounds.

        Raises
        ------
        ValueError if ci_method is not supported.
        """
        data, series, obs_start, obs_end = self._base_data()

        obs_duration  = (obs_end - obs_start).dt.days.values.astype(float)

        # Compute time_to_first for each entity — NaN if no occurrence
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
