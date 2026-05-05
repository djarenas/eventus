"""
cohort_timeline_occurrence_analyzer.py
CohortTimelineOccurrenceAnalyzer — occurrence statistics for one identity
within a CohortTimeline.
"""
from __future__ import annotations
import pandas as pd

from eventus.cohort_timeline.cohort_timeline import CohortTimeline
from . import cohort_timeline_occurrence_analyzer_utils as utils

_ERROR = "[CohortTimelineOccurrenceAnalyzer] Error"


class CohortTimelineOccurrenceAnalyzer:
    """
    I compute occurrence statistics for one occurrence identity within
    a CohortTimeline.

    Raises at construction if:
    - no obs period on the CohortTimeline
    - identity not in ct.occurrence_identities
    - occ_{identity}_n already exists (already analyzed)
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
        utils.require_identity_present(identity, cohort_timeline.occurrence_identities)
        utils.require_not_already_analyzed(identity, cohort_timeline.data.columns.tolist())

        self._ct       = cohort_timeline
        self._identity = identity

    @property
    def identity(self) -> str:
        return self._identity

    def compute_stats(self, extras=None) -> CohortTimeline:
        extras_list = utils.validate_extras(extras)
        data        = self._ct.data.copy()
        obs_start   = pd.to_datetime(data["obs_start"]).dt.normalize()
        obs_end     = pd.to_datetime(data["obs_end"]).dt.normalize()

        stats_df = utils.analyze_occurrence_column(
            series    = data[f"occ_{self._identity}"],
            obs_start = obs_start,
            obs_end   = obs_end,
            extras    = extras_list,
        )
        for stat_name in stats_df.columns:
            data[f"occ_{self._identity}_{stat_name}"] = stats_df[stat_name].values

        return CohortTimeline(data, self._ct.entity_col)

    def summary(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        utils.require_stats_exist(
            self._identity, self._ct.data.columns.tolist(), "summary"
        )
        return utils.calc_occ_summary(self._ct.data, self._ct.entity_col, percentiles)

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"CohortTimelineOccurrenceAnalyzer(\n"
            f"  identity  : '{self._identity}'\n"
            f"  entities  : {len(self._ct):,}\n"
            f"  has_stats : {f'occ_{self._identity}_n' in self._ct.data.columns}\n"
            f")"
        )
