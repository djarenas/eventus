"""
episode_event_interaction_analyzer.py
EpisodeEventInteractionAnalyzer — cross-type analysis of events
relative to episode structure within a CohortTimeline.

This is the final permutation of the three core object types:
    Events × ObsPeriod   → CohortTimelineEventAnalyzer
    Episodes × ObsPeriod → CohortTimelineEpisodeAnalyzer
    Events × Events      → EventCoOccurrenceAnalyzer
    Events × Episodes    → EpisodeEventInteractionAnalyzer  ← this class

Methods
-------
compute_interaction() → EpisodeEventInteractionResult
"""
from __future__ import annotations

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.episode_event_interaction_result import (
    EpisodeEventInteractionResult,
)
from . import episode_event_interaction_analyzer_utils as utils

_ERROR = "[EpisodeEventInteractionAnalyzer] Error"


class EpisodeEventInteractionAnalyzer:
    """
    I compute per-entity event counts classified by their position
    relative to a member's episode structure:

        - before the first episode
        - during active episodes
        - during gaps between episodes
        - after the last episode
        - for members with no episodes at all

    Raises at construction if:
    - cohort_timeline is not a CohortTimeline
    - cohort_timeline has no observation period
    - episode_identity not in cohort_timeline.episode_identities
    - event_identity not in cohort_timeline.event_identities
    """

    # ── Attributes ────────────────────────────────────────────────────
    _ct:               CohortTimeline
    _episode_identity: str
    _event_identity:   str

    def __init__(
        self,
        cohort_timeline:  CohortTimeline,
        episode_identity: str,
        event_identity:   str,
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
        for name, val, valid in [
            ("episode_identity", episode_identity, cohort_timeline.episode_identities),
            ("event_identity",   event_identity,   cohort_timeline.event_identities),
        ]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(
                    f"{_ERROR} {name} must be a non-empty string, got {val!r}"
                )
            if val not in valid:
                raise ValueError(
                    f"{_ERROR} {name} '{val}' not found. "
                    f"Available: {valid}"
                )

        self._ct               = cohort_timeline
        self._episode_identity = episode_identity
        self._event_identity   = event_identity

    # ── Properties ────────────────────────────────────────────────────

    @property
    def episode_identity(self) -> str:
        return self._episode_identity

    @property
    def event_identity(self) -> str:
        return self._event_identity

    @property
    def cohort_timeline(self) -> CohortTimeline:
        return self._ct

    # ── Public methods ────────────────────────────────────────────────

    def compute_interaction(self) -> EpisodeEventInteractionResult:
        """
        Classify each entity's events by their position relative to
        the episode structure.

        Returns
        -------
        EpisodeEventInteractionResult
            One row per entity. Columns: n_before, n_during, n_gaps,
            n_after, n_no_episodes. NaN where semantically absent.
        """
        data     = self._ct.data
        stats_df = utils.compute_interaction_stats(
            data             = data,
            entity_col       = self._ct.entity_col,
            episode_identity = self._episode_identity,
            event_identity   = self._event_identity,
        )

        result_data = data[[self._ct.entity_col]].copy()
        result_data["obs_start"] = data["obs_start"].values
        result_data["obs_end"]   = data["obs_end"].values
        for col in stats_df.columns:
            result_data[col] = stats_df[col].values

        return EpisodeEventInteractionResult(
            data             = result_data,
            entity_col       = self._ct.entity_col,
            episode_identity = self._episode_identity,
            event_identity   = self._event_identity,
        )

    # ── Dunder ────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._ct)

    def __repr__(self) -> str:
        return (
            f"EpisodeEventInteractionAnalyzer(\n"
            f"  episode_identity : '{self._episode_identity}'\n"
            f"  event_identity   : '{self._event_identity}'\n"
            f"  entities         : {len(self._ct):,}\n"
            f")"
        )
