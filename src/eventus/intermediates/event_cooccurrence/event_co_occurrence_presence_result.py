"""
event_co_occurrence_presence_result.py
EventCoOccurrencePresenceResult — per-entity presence statistics for
two event identities within a CohortTimeline.

Produced by
-----------
EventCoOccurrenceAnalyzer.compute_presence()

This object answers one question: do A and B co-occur in the same
observation period above what chance would predict?

For windowed co-occurrence analysis (did B happen within N days of A?)
see EventCoOccurrenceWindowedResult, produced by
EventCoOccurrenceAnalyzer.compute_windowed_presence(within_days).
"""
from __future__ import annotations
import math
import pandas as pd

from eventus.intermediates.event_cooccurrence.event_co_occurrence_result import EventCoOccurrenceResult

_ERROR = "[EventCoOccurrencePresenceResult] Error"

_REQUIRED_COLS = {
    "n_a", "n_b",
    "has_a", "has_b", "has_both",
}

_FISHER_NOTE = (
    "Two-sided Fisher's exact test on the 2x2 co-occurrence table. "
    "Tests whether A and B co-occur independently within the observation "
    "period. Tests independence only — does not describe mechanisms, "
    "directionality, or temporal relationships."
)


class EventCoOccurrencePresenceResult(EventCoOccurrenceResult):
    """
    Per-entity presence statistics for two event identities within a
    CohortTimeline.

    Produced by
    -----------
    EventCoOccurrenceAnalyzer.compute_presence()

    Answers: do A and B co-occur in the same observation period more
    than chance would predict?

    Parameters
    ----------
    data       : pd.DataFrame — one row per entity, see columns below.
    entity_col : str
    identity_a : str
    identity_b : str

    Columns in data (beyond entity_col, obs_start, obs_end)
    -------------------------------------------------------
    n_a      : int  — count of A events in obs period
    n_b      : int  — count of B events in obs period
    has_a    : bool — entity had at least one A event
    has_b    : bool — entity had at least one B event
    has_both : bool — entity had at least one A and at least one B

    NaN semantics
    -------------
    No NaN values in the required columns — every entity has a
    definitive presence status.

    Statistical note
    ----------------
    Fisher's exact p-value is computed at construction from the 2x2
    contingency table. It tests independence of A and B presence in
    the observation period. See fisher_exact_note for full
    interpretation guidance.
    """

    # ── Attributes ───────────────────────────────────────────────────────
    # Inherited from EventCoOccurrenceResult
    _data:        pd.DataFrame                          # validated per-entity DataFrame
    _entity_col:  str                                   # entity identifier column name
    _identity_a:  str                                   # first event identity label
    _identity_b:  str                                   # second event identity label
    # Own
    _fisher_p:    float                                 # two-sided Fisher exact p-value
    _association: "EventCoOccurrenceAssociation | None" # lazily computed, cached

    def __init__(
        self,
        data:       pd.DataFrame,
        entity_col: str,
        identity_a: str,
        identity_b: str,
    ) -> None:
        super().__init__(data, entity_col, identity_a, identity_b)

        missing = _REQUIRED_COLS - set(self._data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR}: data is missing required columns: {sorted(missing)}."
            )

        from scipy.stats import fisher_exact as _fisher_exact

        n_with_both = int((self._data["has_a"] & self._data["has_b"]).sum())
        n_a_only    = int((self._data["has_a"] & ~self._data["has_b"]).sum())
        n_b_only    = int((~self._data["has_a"] & self._data["has_b"]).sum())
        n_neither   = int((~self._data["has_a"] & ~self._data["has_b"]).sum())

        _, p = _fisher_exact(
            [[n_with_both, n_a_only],
             [n_b_only,    n_neither]],
            alternative="two-sided",
        )
        self._fisher_p    = float(p)
        self._association = None

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
    def n_with_neither(self) -> int:
        """Entities with neither A nor B."""
        return int((~self._data["has_a"] & ~self._data["has_b"]).sum())

    @property
    def p_b_given_a(self) -> float:
        """P(B | A) — fraction of entities with A that also have B."""
        n_a = self.n_with_a
        if n_a == 0:
            return float("nan")
        return round(self.n_with_both / n_a, 4)

    @property
    def p_b_given_no_a(self) -> float:
        """P(B | no A) — fraction of entities without A that have B."""
        n_no_a = self.n_entities - self.n_with_a
        if n_no_a == 0:
            return float("nan")
        n_b_only = int((~self._data["has_a"] & self._data["has_b"]).sum())
        return round(n_b_only / n_no_a, 4)

    @property
    def prevalence_ratio(self) -> float:
        """P(B | A) / P(B | no A)."""
        p_a = self.p_b_given_a
        p_no_a = self.p_b_given_no_a
        if math.isnan(p_a) or math.isnan(p_no_a) or p_no_a == 0:
            return float("nan")
        return round(p_a / p_no_a, 3)

    @property
    def fisher_exact_p(self) -> float:
        """Two-sided Fisher's exact p-value. Computed at construction."""
        return self._fisher_p

    @property
    def fisher_exact_note(self) -> str:
        """Interpretation guidance for fisher_exact_p."""
        return _FISHER_NOTE

    @property
    def association(self) -> "EventCoOccurrenceAssociation":
        """
        Full association analysis derived from the 2x2 contingency table.
        Conditional probabilities with Wilson CIs, prevalence ratio with
        log-method CI, and a disclaimer. No additional data needed beyond
        what compute_presence() already computed.
        """
        if self._association is None:
            from eventus.intermediates.event_cooccurrence.event_co_occurrence_association import (
                EventCoOccurrenceAssociation,
            )
            self._association = EventCoOccurrenceAssociation(
                n_with_both = self.n_with_both,
                n_a_only    = int(
                    (self._data["has_a"] & ~self._data["has_b"]).sum()
                ),
                n_b_only    = int(
                    (~self._data["has_a"] & self._data["has_b"]).sum()
                ),
                n_neither   = self.n_with_neither,
                identity_a  = self._identity_a,
                identity_b  = self._identity_b,
            )
        return self._association

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100 * x / n, 1)}%)" if n else str(x)

        def fmt_p(p):
            if math.isnan(p):
                return "NaN"
            if p < 0.001:
                return f"{p:.2e}"
            return f"{p:.4f}"

        return (
            f"EventCoOccurrencePresenceResult:\n"
            f"  identity_a        : {self._identity_a}\n"
            f"  identity_b        : {self._identity_b}\n"
            f"  entity_col        : {self._entity_col}\n"
            f"  entities          : {n:,}\n"
            f"  {chr(8212) * 44}\n"
            f"  n_with_a          : {pct(self.n_with_a)}\n"
            f"  n_with_b          : {pct(self.n_with_b)}\n"
            f"  n_with_both       : {pct(self.n_with_both)}\n"
            f"  n_with_neither    : {pct(self.n_with_neither)}\n"
            f"  {chr(8212) * 44}\n"
            f"  p_b_given_a       : {round(self.p_b_given_a * 100, 1) if not math.isnan(self.p_b_given_a) else chr(78)+chr(97)+chr(78)}%\n"
            f"  p_b_given_no_a    : {round(self.p_b_given_no_a * 100, 1) if not math.isnan(self.p_b_given_no_a) else chr(78)+chr(97)+chr(78)}%\n"
            f"  prevalence_ratio  : {self.prevalence_ratio}x\n"
            f"  {chr(8212) * 44}\n"
            f"  fisher_exact_p    : {fmt_p(self._fisher_p)}\n"
        )
