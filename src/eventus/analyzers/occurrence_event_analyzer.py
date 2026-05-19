"""
occurrence_event_analyzer.py
OccurrenceEventAnalyzer — temporal relationship analysis between
one occurrence identity and one event identity within a CohortTimeline.

Methods
-------
compute() → OccurrenceEventResult
"""
from __future__ import annotations

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.occurrence_event_result import OccurrenceEventResult
import eventus.analyzers.occurrence_event_analyzer_utils as utils

_ERROR = "[OccurrenceEventAnalyzer] Error"


class OccurrenceEventAnalyzer:
    """
    I compute temporal relationship statistics between one occurrence
    identity and one event identity within a CohortTimeline.

    Raises at construction if:
    - cohort_timeline is not a CohortTimeline
    - cohort_timeline has no observation period
    - occurrence_identity not in cohort_timeline.occurrence_identities
    - event_identity not in cohort_timeline.event_identities

    Parameters
    ----------
    cohort_timeline      : CohortTimeline
    occurrence_identity  : str   e.g. "ed_visit"
    event_identity       : str   e.g. "inpatient_hospitalization"
    """

    _ct:                  CohortTimeline
    _occurrence_identity: str
    _event_identity:      str

    def __init__(
        self,
        cohort_timeline:     CohortTimeline,
        occurrence_identity: str,
        event_identity:      str,
    ) -> None:
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR} cohort_timeline must be a CohortTimeline, "
                f"got {type(cohort_timeline).__name__}"
            )
        if not cohort_timeline.has_obs_period:
            raise ValueError(
                f"{_ERROR} CohortTimeline has no observation period. "
                f"obs_start and obs_end are required."
            )
        if not isinstance(occurrence_identity, str) or not occurrence_identity.strip():
            raise TypeError(
                f"{_ERROR} occurrence_identity must be a non-empty string."
            )
        if not isinstance(event_identity, str) or not event_identity.strip():
            raise TypeError(
                f"{_ERROR} event_identity must be a non-empty string."
            )
        if occurrence_identity not in cohort_timeline.occurrence_identities:
            raise ValueError(
                f"{_ERROR} occurrence_identity '{occurrence_identity}' not found. "
                f"Available: {cohort_timeline.occurrence_identities}"
            )
        if event_identity not in cohort_timeline.event_identities:
            raise ValueError(
                f"{_ERROR} event_identity '{event_identity}' not found. "
                f"Available: {cohort_timeline.event_identities}"
            )

        self._ct                  = cohort_timeline
        self._occurrence_identity = occurrence_identity
        self._event_identity      = event_identity

    # ── Public API ────────────────────────────────────────────────────────────

    def compute(self) -> OccurrenceEventResult:
        """
        Compute per-entity temporal relationship statistics.

        Returns
        -------
        OccurrenceEventResult
            One row per entity with within counts and gap stats.
        """
        data = self._ct.data

        occ_col        = f"occ_{self._occurrence_identity}"
        starts_col     = f"evt_{self._event_identity}_starts"
        ends_col       = f"evt_{self._event_identity}_ends"
        obs_start_col  = "obs_start"
        obs_end_col    = "obs_end"

        stats_df = utils.compute_all_entities(
            data           = data,
            entity_col     = self._ct.entity_col,
            occ_col        = occ_col,
            evt_starts_col = starts_col,
            evt_ends_col   = ends_col,
            obs_start_col  = obs_start_col,
            obs_end_col    = obs_end_col,
        )

        # Reorder — entity first, then obs, then stats
        col_order = (
            [self._ct.entity_col, obs_start_col, obs_end_col] +
            [c for c in stats_df.columns
             if c not in [self._ct.entity_col, obs_start_col, obs_end_col]]
        )
        stats_df = stats_df[col_order].reset_index(drop=True)

        return OccurrenceEventResult(
            data           = stats_df,
            entity_col     = self._ct.entity_col,
            identity_occ   = self._occurrence_identity,
            identity_event = self._event_identity,
        )

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"OccurrenceEventAnalyzer(\n"
            f"  occurrence_identity : '{self._occurrence_identity}'\n"
            f"  event_identity      : '{self._event_identity}'\n"
            f"  entities            : {len(self._ct):,}\n"
            f")"
        )
