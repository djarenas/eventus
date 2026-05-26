"""
event_episode_analyzer.py
EventEpisodeAnalyzer — temporal relationship analysis between
one event identity and one episode identity within a CohortTimeline.

Methods
-------
compute() → EventEpisodeResult
"""
from __future__ import annotations

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.event_episode_result import EventEpisodeResult
import eventus.analyzers.event_episode_analyzer_utils as utils

_ERROR = "[EventEpisodeAnalyzer] Error"


class EventEpisodeAnalyzer:
    """
    I compute temporal relationship statistics between one event
    identity and one episode identity within a CohortTimeline.

    Raises at construction if:
    - cohort_timeline is not a CohortTimeline
    - cohort_timeline has no observation period
    - event_identity not in cohort_timeline.event_identities
    - episode_identity not in cohort_timeline.episode_identities

    Parameters
    ----------
    cohort_timeline      : CohortTimeline
    event_identity  : str   e.g. "ed_visit"
    episode_identity       : str   e.g. "inpatient_hospitalization"
    """

    _ct:                  CohortTimeline
    _event_identity: str
    _episode_identity:      str

    def __init__(
        self,
        cohort_timeline:     CohortTimeline,
        event_identity: str,
        episode_identity:      str,
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
        if not isinstance(event_identity, str) or not event_identity.strip():
            raise TypeError(
                f"{_ERROR} event_identity must be a non-empty string."
            )
        if not isinstance(episode_identity, str) or not episode_identity.strip():
            raise TypeError(
                f"{_ERROR} episode_identity must be a non-empty string."
            )
        if event_identity not in cohort_timeline.event_identities:
            raise ValueError(
                f"{_ERROR} event_identity '{event_identity}' not found. "
                f"Available: {cohort_timeline.event_identities}"
            )
        if episode_identity not in cohort_timeline.episode_identities:
            raise ValueError(
                f"{_ERROR} episode_identity '{episode_identity}' not found. "
                f"Available: {cohort_timeline.episode_identities}"
            )

        self._ct                  = cohort_timeline
        self._event_identity = event_identity
        self._episode_identity      = episode_identity

    # ── Public API ────────────────────────────────────────────────────────────

    def compute(self) -> EventEpisodeResult:
        """
        Compute per-entity temporal relationship statistics.

        Returns
        -------
        EventEpisodeResult
            One row per entity with within counts and gap stats.
        """
        data = self._ct.data

        evt_col        = f"evt_{self._event_identity}"
        starts_col     = f"eps_{self._episode_identity}_starts"
        ends_col       = f"eps_{self._episode_identity}_ends"
        obs_start_col  = "obs_start"
        obs_end_col    = "obs_end"

        stats_df = utils.compute_all_entities(
            data           = data,
            entity_col     = self._ct.entity_col,
            evt_col        = evt_col,
            eps_starts_col = starts_col,
            eps_ends_col   = ends_col,
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

        return EventEpisodeResult(
            data           = stats_df,
            entity_col     = self._ct.entity_col,
            identity_occ   = self._event_identity,
            identity_episode = self._episode_identity,
        )

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"EventEpisodeAnalyzer(\n"
            f"  event_identity : '{self._event_identity}'\n"
            f"  episode_identity      : '{self._episode_identity}'\n"
            f"  entities            : {len(self._ct):,}\n"
            f")"
        )
