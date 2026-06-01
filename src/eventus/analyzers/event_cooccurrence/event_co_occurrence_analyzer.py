"""
event_co_occurrence_analyzer.py
EventCoOccurrenceAnalyzer — co-occurrence analysis between two event
identities within a CohortTimeline.

Methods
-------
compute_presence()              → EventCoOccurrencePresenceResult
compute_gaps()                  → EventCoOccurrenceGapResult

Planned (not yet implemented)
------------------------------
compute_windowed_presence(within_days) → EventCoOccurrenceWindowedResult
compute_directionality()               → EventCoOccurrenceDirectionalityResult
compute_survival()                     → EventCoOccurrenceSurvivalResult
"""
from __future__ import annotations

from eventus.intermediates.cohort_timeline import CohortTimeline

_ERROR = "[EventCoOccurrenceAnalyzer] Error"


class EventCoOccurrenceAnalyzer:
    """
    Co-occurrence analysis between two event identities within a
    CohortTimeline.

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
    ...     identity_a      = "cirrhosis_diagnosis",
    ...     identity_b      = "ed_visit",
    ... )
    >>> presence = analyzer.compute_presence()
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
    # Group A — Presence
    # ------------------------------------------------------------------ #

    def compute_presence(self) -> "EventCoOccurrencePresenceResult":
        """
        Compute per-entity presence statistics for identity_a and
        identity_b within the observation period.

        Answers: do A and B co-occur in the same observation period
        more than chance would predict?

        For each entity, records whether they had at least one A event,
        at least one B event, or both — then computes P(B|A), P(B|no A),
        prevalence ratio, and Fisher's exact p-value across the cohort.

        Returns
        -------
        EventCoOccurrencePresenceResult
            One row per entity. Columns: n_a, n_b, has_a, has_b,
            has_both. Cohort-level properties: n_with_a, n_with_b,
            n_with_both, n_with_neither, p_b_given_a, p_b_given_no_a,
            prevalence_ratio, fisher_exact_p.
        """
        from eventus.intermediates.event_cooccurrence.event_co_occurrence_presence_result import (
            EventCoOccurrencePresenceResult,
        )
        from eventus.analyzers.event_cooccurrence.event_co_occurrence_presence_utils import (
            compute_presence_stats,
        )

        stats_df = compute_presence_stats(
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

        return EventCoOccurrencePresenceResult(
            data       = stats_df,
            entity_col = self._ct.entity_col,
            identity_a = self._identity_a,
            identity_b = self._identity_b,
        )

    # ------------------------------------------------------------------ #
    # Group B — Gaps
    # ------------------------------------------------------------------ #

    def compute_gaps(self) -> "EventCoOccurrenceGapSummary":
        """
        Compute per-entity nearest-gap statistics between identity_a
        and identity_b.

        For each A event, finds the nearest B event in either direction
        (before or after) and records the absolute gap in days. The
        median across all A events for an entity is stored. Same logic
        applies B→nearest A.

        Only entities with both n_a > 0 and n_b > 0 have non-NaN gap
        values. All entities are present in the result — check n_a and
        n_b to understand why a gap is NaN.

        Returns
        -------
        EventCoOccurrenceGapSummary
            One row per entity. Columns: n_a, n_b,
            median_gap_a_to_nearest_b, median_gap_b_to_nearest_a.

        Notes
        -----
        Gap is absolute (direction-agnostic). For directionality
        analysis see the planned compute_directionality() method.
        For statistical testing against an analytical null see
        EventCoOccurrenceGapAnalyzer.
        """
        from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_summary import (
            EventCoOccurrenceGapSummary,
        )
        from eventus.analyzers.event_cooccurrence.event_co_occurrence_gap_utils import (
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

        return EventCoOccurrenceGapSummary(
            data       = stats_df,
            entity_col = self._ct.entity_col,
            identity_a = self._identity_a,
            identity_b = self._identity_b,
        )

    def compute_directionality(self) -> "EventCoOccurrenceDirectionalitySummary":
        """
        Compute per-entity mean signed gap statistics between
        identity_a and identity_b.

        For each A event, finds the nearest B event in either direction
        and records the signed gap: positive if B is after A, negative
        if before. Takes the mean across all A events for each entity.

        Positive cohort_mean_signed_gap → A tends to precede B.
        Negative → B tends to precede A.
        Zero → no consistent ordering.

        Returns
        -------
        EventCoOccurrenceDirectionalitySummary
            One row per entity. Columns: n_a, n_b, mean_signed_gap.

        Notes
        -----
        Uses mean (not median) aggregation — the right choice for
        signed gaps where direction matters. See chapter 10.
        For absolute gap proximity see compute_gaps() (chapter 9).
        For statistical testing see EventCoOccurrenceDirectionalityAnalyzer.
        """
        from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_summary import (
            EventCoOccurrenceDirectionalitySummary,
        )
        from eventus.analyzers.event_cooccurrence.event_co_occurrence_directionality_utils import (
            compute_directionality_stats,
        )

        stats_df = compute_directionality_stats(
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

        return EventCoOccurrenceDirectionalitySummary(
            data       = stats_df,
            entity_col = self._ct.entity_col,
            identity_a = self._identity_a,
            identity_b = self._identity_b,
        )

    # ------------------------------------------------------------------ #
    # Planned — not yet implemented
    # ------------------------------------------------------------------ #
    #
    # compute_windowed_presence(within_days) → EventCoOccurrenceWindowedResult
    #     Per-entity windowed co-occurrence: did B happen within N days
    #     of A? Answers a temporal proximity question, not just presence.
    #     within_days=30 means any (A, B) pair within 30 days counts.
    #
    # compute_directionality() → EventCoOccurrenceDirectionalityResult
    #     Per-entity ordering: among co-occurring pairs, does A tend to
    #     precede B? Binomial sign test across the cohort.
    #
    # compute_survival() → EventCoOccurrenceSurvivalResult
    #     Time-to-event from A to first B after A. Entities with no B
    #     after any A are right-censored. Kaplan-Meier + log-rank test.

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
