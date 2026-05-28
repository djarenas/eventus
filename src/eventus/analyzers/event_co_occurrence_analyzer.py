"""
event_co_occurrence_analyzer.py
EventCoOccurrenceAnalyzer — co-occurrence analysis between two event
identities within a CohortTimeline.

Methods
-------
compute_presence(within_days)  → EventCoOccurrencePresenceResult
compute_gaps()                 → EventCoOccurrenceGapResult

Planned (not yet implemented)
------------------------------
compute_proximity(within_days) → EventCoOccurrenceProximityResult
compute_transitions()          → EventCoOccurrenceTransitionResult
compute_association()          → EventCoOccurrenceAssociationResult
"""
from __future__ import annotations

from eventus.intermediates.cohort_timeline import CohortTimeline

_ERROR = "[EventCoOccurrenceAnalyzer] Error"


class EventCoOccurrenceAnalyzer:
    """
    Co-occurrence analysis between two event identities within a
    CohortTimeline.

    Computes per-entity presence, same-day co-occurrence, and
    nearest-neighbor gap statistics between identity_a and identity_b.

    Parameters
    ----------
    cohort_timeline : CohortTimeline
        Must contain an observation period and both event identities.
    identity_a : str
        First event identity. Must be in cohort_timeline.event_identities.
    identity_b : str
        Second event identity. Must be in cohort_timeline.event_identities.
        Must differ from identity_a.

    Raises
    ------
    TypeError
        If cohort_timeline is not a CohortTimeline.
    ValueError
        If cohort_timeline has no observation period.
        If identity_a or identity_b not in event_identities.
        If identity_a == identity_b.

    Examples
    --------
    >>> analyzer = EventCoOccurrenceAnalyzer(
    ...     cohort_timeline = ct,
    ...     identity_a      = "ed_visit",
    ...     identity_b      = "specialist_referral",
    ... )
    >>> presence = analyzer.compute_presence(within_days=7)
    >>> gaps     = analyzer.compute_gaps()
    """

    _ct:         CohortTimeline
    _identity_a: str
    _identity_b: str
    _evt_col_a:  str
    _evt_col_b:  str

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        identity_a:      str,
        identity_b:      str,
    ) -> None:
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR}: cohort_timeline must be a CohortTimeline, "
                f"got {type(cohort_timeline).__name__}"
            )
        if not cohort_timeline.has_obs_period:
            raise ValueError(
                f"{_ERROR}: cohort_timeline has no observation period. "
                f"obs_start and obs_end are required."
            )
        for name, val in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(
                    f"{_ERROR}: {name} must be a non-empty string, "
                    f"got {val!r}"
                )
        if identity_a == identity_b:
            raise ValueError(
                f"{_ERROR}: identity_a and identity_b must be different, "
                f"got '{identity_a}' for both."
            )
        for name, identity in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if identity not in cohort_timeline.event_identities:
                raise ValueError(
                    f"{_ERROR}: {name} '{identity}' not found in "
                    f"cohort_timeline.event_identities: "
                    f"{cohort_timeline.event_identities}"
                )

        self._ct         = cohort_timeline
        self._identity_a = identity_a
        self._identity_b = identity_b
        self._evt_col_a  = f"evt_{identity_a}"
        self._evt_col_b  = f"evt_{identity_b}"

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def identity_a(self) -> str:
        return self._identity_a

    @property
    def identity_b(self) -> str:
        return self._identity_b

    @property
    def cohort_timeline(self) -> CohortTimeline:
        return self._ct

    # ------------------------------------------------------------------ #
    # Group A — Presence & same-day co-occurrence
    # ------------------------------------------------------------------ #

    def compute_presence(
        self,
        within_days: int = 0,
    ) -> "EventCoOccurrencePresenceResult":
        """
        Compute per-entity presence and same-day co-occurrence statistics.

        Parameters
        ----------
        within_days : int
            Window in days for counting (A, B) pairs that fell within
            this many days of each other (in either direction).
            0 (default) = same-day pairs only.
            Must be a non-negative integer.

        Returns
        -------
        EventCoOccurrencePresenceResult
            One row per entity. Columns: n_a, n_b, has_a, has_b,
            has_both, n_same_day, pct_a_with_same_day_b,
            pct_b_with_same_day_a, n_co_occurrences_within.
        """
        from eventus.intermediates.event_co_occurrence_presence_result import (
            EventCoOccurrencePresenceResult,
        )
        from eventus.analyzers.event_co_occurrence_presence_utils import (
            compute_presence_stats,
        )

        if not isinstance(within_days, int) or within_days < 0:
            raise ValueError(
                f"{_ERROR} in compute_presence(): within_days must be a "
                f"non-negative integer, got {within_days!r}"
            )

        stats_df = compute_presence_stats(
            data        = self._ct.data,
            entity_col  = self._ct.entity_col,
            evt_col_a   = self._evt_col_a,
            evt_col_b   = self._evt_col_b,
            within_days = within_days,
        )

        col_order = (
            [self._ct.entity_col, "obs_start", "obs_end"] +
            [c for c in stats_df.columns
             if c not in {self._ct.entity_col, "obs_start", "obs_end"}]
        )
        stats_df = stats_df[col_order].reset_index(drop=True)

        return EventCoOccurrencePresenceResult(
            data        = stats_df,
            entity_col  = self._ct.entity_col,
            identity_a  = self._identity_a,
            identity_b  = self._identity_b,
            within_days = within_days,
        )

    # ------------------------------------------------------------------ #
    # Group B — Gaps
    # ------------------------------------------------------------------ #

    def compute_gaps(self) -> "EventCoOccurrenceGapResult":
        """
        Compute per-entity nearest-neighbor gap statistics between
        identity_a and identity_b.

        No window is applied — gaps are computed over the full
        observation period. For each A event, the nearest B that occurs
        strictly after it is found; and vice versa.

        Returns
        -------
        EventCoOccurrenceGapResult
            One row per entity. Columns: n_a_with_following_b,
            mean/median/std_days_a_to_b, n_b_with_following_a,
            mean/median/std_days_b_to_a.
        """
        from eventus.intermediates.event_co_occurrence_gap_result import (
            EventCoOccurrenceGapResult,
        )
        from eventus.analyzers.event_co_occurrence_gap_utils import (
            compute_gap_stats,
        )

        stats_df = compute_gap_stats(
            data       = self._ct.data,
            entity_col = self._ct.entity_col,
            evt_col_a  = self._evt_col_a,
            evt_col_b  = self._evt_col_b,
        )

        col_order = (
            [self._ct.entity_col, "obs_start", "obs_end"] +
            [c for c in stats_df.columns
             if c not in {self._ct.entity_col, "obs_start", "obs_end"}]
        )
        stats_df = stats_df[col_order].reset_index(drop=True)

        return EventCoOccurrenceGapResult(
            data       = stats_df,
            entity_col = self._ct.entity_col,
            identity_a = self._identity_a,
            identity_b = self._identity_b,
        )

    # ------------------------------------------------------------------ #
    # Group C — planned, not yet implemented
    # ------------------------------------------------------------------ #
    #
    # compute_proximity(within_days=30) → EventCoOccurrenceProximityResult
    #     Per-entity TTE distribution: given A, how long until B?
    #     Entities with no B after any A are right-censored.
    #
    # compute_transitions() → EventCoOccurrenceTransitionResult
    #     Markov-style transition probabilities: merge both streams into
    #     a unified per-entity timeline, compute P(next=B | current=A)
    #     and P(next=A | current=B).
    #
    # compute_association() → EventCoOccurrenceAssociationResult
    #     Odds ratio / relative risk from a 2×2 contingency table of
    #     time windows. Answers: "is B actually tied to A, or does B
    #     just happen all the time anyway?"

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventCoOccurrenceAnalyzer(\n"
            f"  identity_a : '{self._identity_a}'\n"
            f"  identity_b : '{self._identity_b}'\n"
            f"  entities   : {len(self._ct):,}\n"
            f")"
        )
