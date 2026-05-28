"""
event_co_occurrence_gap_result.py
EventCoOccurrenceGapResult — per-entity nearest-neighbor gap statistics
between two event identities.

Produced by
-----------
EventCoOccurrenceAnalyzer.compute_gaps()
"""
from __future__ import annotations
import pandas as pd

from eventus.intermediates.event_co_occurrence_result import EventCoOccurrenceResult

_ERROR = "[EventCoOccurrenceGapResult] Error"

_REQUIRED_COLS = {
    "n_a_with_following_b",
    "mean_days_a_to_b",
    "median_days_a_to_b",
    "std_days_a_to_b",
    "n_b_with_following_a",
    "mean_days_b_to_a",
    "median_days_b_to_a",
    "std_days_b_to_a",
}


class EventCoOccurrenceGapResult(EventCoOccurrenceResult):
    """
    Per-entity nearest-neighbor gap statistics between two event
    identities within a CohortTimeline.

    Produced by
    -----------
    EventCoOccurrenceAnalyzer.compute_gaps()

    Attributes (beyond base class)
    ------------------------------
    See EventCoOccurrenceResult for: _data, _entity_col, _identity_a, _identity_b.
    This subclass adds no additional instance attributes — all columns are
    accessed via self._data.

    # ── All instance attributes — inherited and own ──────────────────
    # (declared here so the full picture is visible without reading parent)
    #   _data:       pd.DataFrame   — one row per entity
    #   _entity_col: str            — entity identifier column
    #   _identity_a: str            — first event identity
    #   _identity_b: str            — second event identity
    # Own: none beyond the base class

    No window is applied — gaps are computed over the full observation
    period using nearest-neighbor logic. For each A event, the nearest
    B that occurs strictly after it is found; and vice versa.

    Columns in data (beyond entity_col, obs_start, obs_end)
    -------------------------------------------------------
    A → nearest B after each A:
        n_a_with_following_b : int   — A events with any B after them
        mean_days_a_to_b     : float — mean of nearest-B gaps. NaN if
                                       n_a_with_following_b = 0.
        median_days_a_to_b   : float — NaN if n_a_with_following_b = 0.
        std_days_a_to_b      : float — NaN if < 2 qualifying pairs.

    B → nearest A after each B:
        n_b_with_following_a : int   — B events with any A after them
        mean_days_b_to_a     : float — NaN if n_b_with_following_a = 0.
        median_days_b_to_a   : float — NaN if n_b_with_following_a = 0.
        std_days_b_to_a      : float — NaN if < 2 qualifying pairs.

    NaN semantics
    -------------
    NaN in gap statistics may mean: entity had no A events, entity had
    no B events, or entity had both but no qualifying forward pairs in
    the observation period. All are scientifically valid — absent signal,
    not missing data.
    """

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

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def n_with_a_to_b_gap(self) -> int:
        """Entities with at least one qualifying A → B pair."""
        return int(self._data["mean_days_a_to_b"].notna().sum())

    @property
    def n_with_b_to_a_gap(self) -> int:
        """Entities with at least one qualifying B → A pair."""
        return int(self._data["mean_days_b_to_a"].notna().sum())

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100 * x / n, 1)}%)" if n else str(x)

        med_a_to_b = round(
            float(self._data["median_days_a_to_b"].dropna().median()), 1
        ) if self._data["median_days_a_to_b"].notna().any() else "NaN"

        med_b_to_a = round(
            float(self._data["median_days_b_to_a"].dropna().median()), 1
        ) if self._data["median_days_b_to_a"].notna().any() else "NaN"

        return (
            f"EventCoOccurrenceGapResult:\n"
            f"  identity_a              : {self._identity_a}\n"
            f"  identity_b              : {self._identity_b}\n"
            f"  entity_col              : {self._entity_col}\n"
            f"  entities                : {n:,}\n"
            f"  {'─' * 44}\n"
            f"  n_with_a_to_b_gap       : {pct(self.n_with_a_to_b_gap)}\n"
            f"  median_a_to_b (cohort)  : {med_a_to_b} days\n"
            f"  n_with_b_to_a_gap       : {pct(self.n_with_b_to_a_gap)}\n"
            f"  median_b_to_a (cohort)  : {med_b_to_a} days\n"
        )
