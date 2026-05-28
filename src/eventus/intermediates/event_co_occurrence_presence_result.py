"""
event_co_occurrence_presence_result.py
EventCoOccurrencePresenceResult — per-entity presence and same-day
co-occurrence statistics for two event identities.

Produced by
-----------
EventCoOccurrenceAnalyzer.compute_presence(within_days)
"""
from __future__ import annotations
import pandas as pd

from eventus.intermediates.event_co_occurrence_result import EventCoOccurrenceResult

_ERROR = "[EventCoOccurrencePresenceResult] Error"

_REQUIRED_COLS = {
    "n_a", "n_b",
    "has_a", "has_b", "has_both",
    "n_same_day",
    "pct_a_with_same_day_b",
    "pct_b_with_same_day_a",
    "n_co_occurrences_within",
}


class EventCoOccurrencePresenceResult(EventCoOccurrenceResult):
    """
    Per-entity presence and same-day co-occurrence statistics for
    two event identities within a CohortTimeline.

    Produced by
    -----------
    EventCoOccurrenceAnalyzer.compute_presence(within_days)

    Parameters
    ----------
    data        : pd.DataFrame — one row per entity, see columns below.
    entity_col  : str
    identity_a  : str
    identity_b  : str
    within_days : int — the window used to compute n_co_occurrences_within.
                  0 means same-day only.

    Columns in data (beyond entity_col, obs_start, obs_end)
    -------------------------------------------------------
    n_a                     : int   — count of A events in obs period
    n_b                     : int   — count of B events in obs period
    has_a                   : bool  — entity had at least one A
    has_b                   : bool  — entity had at least one B
    has_both                : bool  — entity had at least one A and one B
    n_same_day              : int   — number of days where both A and B
                                      occurred. Always computed regardless
                                      of within_days.
    pct_a_with_same_day_b   : float — fraction of A events that had a B
                                      on the same day. NaN if n_a = 0.
    pct_b_with_same_day_a   : float — fraction of B events that had an A
                                      on the same day. NaN if n_b = 0.
    n_co_occurrences_within : int   — count of (A, B) pairs where A and B
                                      fell within within_days days of each
                                      other (in either direction).
                                      When within_days=0, equals same-day
                                      pair count. NaN if entity had neither
                                      A nor B.

    NaN semantics
    -------------
    NaN in percentage columns means the denominator was zero — the entity
    had no A events (for pct_a_with_same_day_b) or no B events. This is
    absent signal, not missing data.
    """

    # ── All instance attributes — inherited and own ──────────────────
    # Inherited from EventCoOccurrenceResult
    _data:         pd.DataFrame                           # one row per entity
    _entity_col:   str                                    # entity identifier column
    _identity_a:   str                                    # first event identity
    _identity_b:   str                                    # second event identity
    # Own
    _within_days:  int                                    # window for n_co_occurrences_within
    _association:  "EventCoOccurrenceAssociation | None"  # lazy cache

    def __init__(
        self,
        data:        pd.DataFrame,
        entity_col:  str,
        identity_a:  str,
        identity_b:  str,
        within_days: int,
    ) -> None:
        super().__init__(data, entity_col, identity_a, identity_b)

        if not isinstance(within_days, int) or within_days < 0:
            raise ValueError(
                f"{_ERROR}: within_days must be a non-negative integer, "
                f"got {within_days!r}"
            )

        missing = _REQUIRED_COLS - set(self._data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR}: data is missing required columns: {sorted(missing)}."
            )

        self._within_days   = within_days
        self._association   = None  # lazy cache

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def within_days(self) -> int:
        """The window used to compute n_co_occurrences_within."""
        return self._within_days

    @property
    def n_with_a(self) -> int:
        """Entities with at least one A event."""
        return int(self._data["has_a"].sum())

    @property
    def n_with_b(self) -> int:
        """Entities with at least one B event."""
        return int(self._data["has_b"].sum())

    @property
    def n_with_both(self) -> int:
        """Entities with at least one A and at least one B."""
        return int(self._data["has_both"].sum())

    @property
    def n_with_same_day(self) -> int:
        """Entities with at least one day where both A and B occurred."""
        return int((self._data["n_same_day"] > 0).sum())

    @property
    def n_with_co_occurrence_within(self) -> int:
        """Entities with at least one (A, B) pair within within_days."""
        return int((self._data["n_co_occurrences_within"].fillna(0) > 0).sum())

    # ------------------------------------------------------------------ #
    # Association
    # ------------------------------------------------------------------ #

    @property
    def association(self):
        """
        Derive a full association analysis from the 2x2 contingency table.

        Computes on first access and caches the result. All inputs are
        derived from the presence result - no new data is read.

        Returns
        -------
        EventCoOccurrenceAssociation
        """
        if self._association is None:
            from eventus.intermediates.event_co_occurrence_association import (
                EventCoOccurrenceAssociation,
            )
            n_with_both = int((
                self._data["has_a"] & self._data["has_b"]
            ).sum())
            n_a_only = int((
                self._data["has_a"] & ~self._data["has_b"]
            ).sum())
            n_b_only = int((
                ~self._data["has_a"] & self._data["has_b"]
            ).sum())
            n_neither = int((
                ~self._data["has_a"] & ~self._data["has_b"]
            ).sum())

            self._association = EventCoOccurrenceAssociation(
                n_with_both = n_with_both,
                n_a_only    = n_a_only,
                n_b_only    = n_b_only,
                n_neither   = n_neither,
                identity_a  = self._identity_a,
                identity_b  = self._identity_b,
                within_days = self._within_days,
            )
        return self._association

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100 * x / n, 1)}%)" if n else str(x)

        return (
            f"EventCoOccurrencePresenceResult:\n"
            f"  identity_a               : {self._identity_a}\n"
            f"  identity_b               : {self._identity_b}\n"
            f"  entity_col               : {self._entity_col}\n"
            f"  within_days              : {self._within_days}\n"
            f"  entities                 : {n:,}\n"
            f"  {'─' * 44}\n"
            f"  n_with_a                 : {pct(self.n_with_a)}\n"
            f"  n_with_b                 : {pct(self.n_with_b)}\n"
            f"  n_with_both              : {pct(self.n_with_both)}\n"
            f"  n_with_same_day          : {pct(self.n_with_same_day)}\n"
            f"  n_with_co_occ_within     : {pct(self.n_with_co_occurrence_within)}\n"
        )
