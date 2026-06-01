"""
event_co_occurrence_directionality_summary.py
EventCoOccurrenceDirectionalitySummary — per-entity mean signed gap
statistics for two event identities.

Produced by
-----------
EventCoOccurrenceAnalyzer.compute_directionality()

This object answers: for each co-occurring entity, does A tend to
come before B (positive mean signed gap) or after B (negative)?

Signed gap definition
---------------------
For each A event, find the nearest B event in either direction.
Record the signed gap in days:
  positive = B occurs after A (A precedes B)
  negative = B occurs before A (B precedes A)
  zero     = same day (tie — direction ambiguous)

Take the mean across all A events for that entity. One value per
entity. Entities with n_a=0 or n_b=0 have NaN.

Contrast with EventCoOccurrenceGapSummary
------------------------------------------
Chapter 9 used absolute (direction-agnostic) gaps with median
aggregation — the right choice for measuring temporal proximity.
Chapter 10 uses signed gaps with mean aggregation — the right
choice for measuring directional tendency. Different questions,
different aggregation strategies.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from eventus.intermediates.event_cooccurrence.event_co_occurrence_result import (
    EventCoOccurrenceResult,
)

_ERROR = "[EventCoOccurrenceDirectionalitySummary] Error"

_REQUIRED_COLS = {
    "n_a",
    "n_b",
    "mean_signed_gap",
}


class EventCoOccurrenceDirectionalitySummary(EventCoOccurrenceResult):
    """
    Per-entity mean signed gap statistics for two event identities.

    Produced by
    -----------
    EventCoOccurrenceAnalyzer.compute_directionality()

    Parameters
    ----------
    data       : pd.DataFrame — one row per entity
    entity_col : str
    identity_a : str
    identity_b : str

    Columns in data (beyond entity_col, obs_start, obs_end)
    -------------------------------------------------------
    n_a             : int   — count of A events in obs period
    n_b             : int   — count of B events in obs period
    mean_signed_gap : float — mean of signed nearest-neighbor gaps.
                              Positive = A tends to precede B.
                              Negative = B tends to precede A.
                              Zero = all pairs on same day (tied).
                              NaN if n_a = 0 or n_b = 0.

    NaN semantics
    -------------
    NaN means n_a = 0 or n_b = 0. Check n_a and n_b to understand why.
    This is absent signal, not missing data.
    """

    _data:       pd.DataFrame
    _entity_col: str
    _identity_a: str
    _identity_b: str

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
    # Properties — counts
    # ------------------------------------------------------------------ #

    @property
    def n_co_occurring(self) -> int:
        """Entities with both n_a > 0 and n_b > 0."""
        return int(
            ((self._data["n_a"] > 0) & (self._data["n_b"] > 0)).sum()
        )

    @property
    def n_with_signed_gap(self) -> int:
        """Entities with a non-NaN mean_signed_gap."""
        return int(self._data["mean_signed_gap"].notna().sum())

    @property
    def n_a_first(self) -> int:
        """Entities where mean_signed_gap > 0 (A tends to precede B)."""
        return int((self._data["mean_signed_gap"] > 0).sum())

    @property
    def n_b_first(self) -> int:
        """Entities where mean_signed_gap < 0 (B tends to precede A)."""
        return int((self._data["mean_signed_gap"] < 0).sum())

    @property
    def n_tied(self) -> int:
        """Entities where mean_signed_gap = 0 (all pairs on same day)."""
        return int((self._data["mean_signed_gap"] == 0).sum())

    @property
    def fraction_a_first(self) -> float:
        """
        Fraction of non-tied entities where A tends to precede B.
        Denominator is n_a_first + n_b_first (excludes ties and NaN).
        """
        denom = self.n_a_first + self.n_b_first
        if denom == 0:
            return float("nan")
        return round(self.n_a_first / denom, 4)

    # ------------------------------------------------------------------ #
    # Properties — cohort-level summary
    # ------------------------------------------------------------------ #

    @property
    def cohort_mean_signed_gap(self) -> float:
        """
        Mean of per-entity mean_signed_gap across co-occurring entities.
        Positive = A tends to precede B across the cohort.
        NaN if no entities have a signed gap.
        """
        vals = self._data["mean_signed_gap"].dropna()
        if vals.empty:
            return float("nan")
        return round(float(vals.mean()), 1)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        n  = self.n_entities
        ns = self.n_with_signed_gap

        def pct(x, denom=None):
            d = denom or n
            return f"{x:,} ({round(100 * x / d, 1)}%)" if d else str(x)

        def fmt(v):
            return f"{v:.1f} days" if not math.isnan(v) else "NaN"

        return (
            f"EventCoOccurrenceDirectionalitySummary:\n"
            f"  identity_a               : {self._identity_a}\n"
            f"  identity_b               : {self._identity_b}\n"
            f"  entity_col               : {self._entity_col}\n"
            f"  entities                 : {n:,}\n"
            f"  {'─' * 44}\n"
            f"  n_with_both              : {pct(self.n_co_occurring)}\n"
            f"  n_with_signed_gap        : {pct(self.n_with_signed_gap)}\n"
            f"  {'─' * 44}\n"
            f"  n_a_first                : {pct(self.n_a_first, ns)}  ← {self._identity_a} before {self._identity_b}\n"
            f"  n_b_first                : {pct(self.n_b_first, ns)}  ← {self._identity_b} before {self._identity_a}\n"
            f"  n_tied                   : {self.n_tied:,}\n"
            f"  fraction_a_first         : {round(self.fraction_a_first * 100, 1) if not math.isnan(self.fraction_a_first) else 'NaN'}%\n"
            f"  {'─' * 44}\n"
            f"  cohort_mean_signed_gap   : {fmt(self.cohort_mean_signed_gap)}\n"
        )
