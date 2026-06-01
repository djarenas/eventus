"""
event_co_occurrence_gap_summary.py
EventCoOccurrenceGapSummary — per-entity nearest-gap statistics between
two event identities within a CohortTimeline.

Produced by
-----------
EventCoOccurrenceAnalyzer.compute_gaps()

This object answers: for each entity that had both A and B events,
how far was the nearest B from each A event (and vice versa)?

Gap is defined as absolute days — direction-agnostic. For each A event,
the nearest B in either direction is found. The median across all A
events for that entity is stored. Same logic applies B→nearest A.

For directionality analysis (does A tend to precede B?) see the
planned EventCoOccurrenceDirectionalityResult.
For statistical testing (are gaps shorter than chance?) see
EventCoOccurrenceGapTest, produced by EventCoOccurrenceGapAnalyzer.
"""
from __future__ import annotations
import math
import pandas as pd

from eventus.intermediates.event_cooccurrence.event_co_occurrence_result import (
    EventCoOccurrenceResult,
)

_ERROR = "[EventCoOccurrenceGapSummary] Error"

_REQUIRED_COLS = {
    "n_a",
    "n_b",
    "median_gap_a_to_nearest_b",
    "median_gap_b_to_nearest_a",
}


class EventCoOccurrenceGapSummary(EventCoOccurrenceResult):
    """
    Per-entity nearest-gap statistics for two event identities within
    a CohortTimeline.

    Produced by
    -----------
    EventCoOccurrenceAnalyzer.compute_gaps()

    Answers: for co-occurring entities, how close are A and B events?

    Parameters
    ----------
    data       : pd.DataFrame — one row per entity, see columns below.
    entity_col : str
    identity_a : str
    identity_b : str

    Columns in data (beyond entity_col, obs_start, obs_end)
    -------------------------------------------------------
    n_a                      : int   — count of A events in obs period
    n_b                      : int   — count of B events in obs period
    median_gap_a_to_nearest_b : float — median of (nearest B distance
                                        from each A event), in days.
                                        NaN if n_a = 0 or n_b = 0.
    median_gap_b_to_nearest_a : float — median of (nearest A distance
                                        from each B event), in days.
                                        NaN if n_a = 0 or n_b = 0.

    NaN semantics
    -------------
    NaN in gap columns means n_a = 0 or n_b = 0 — the entity could not
    contribute a gap observation. This is absent signal, not missing data.
    Check n_a and n_b to understand why a gap is NaN.

    Gap definition
    --------------
    Gap is absolute days — direction-agnostic. For each A event, the
    nearest B event in either direction (before or after) is found.
    The gap in days is always non-negative.

    Design notes (future expansion)
    --------------------------------
    - Median chosen over mean to reduce influence of outlier gaps.
      Mean will be available in a future version via analyzer config.
    - Per-entity summary chosen over all-pairs to avoid entities with
      many events dominating the cohort distribution.
      All-pairs mode planned for a future version.
    """

    # All instance attributes — inherited and own
    # Inherited from EventCoOccurrenceResult
    _data:        pd.DataFrame
    _entity_col:  str
    _identity_a:  str
    _identity_b:  str

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
    def n_with_gap_a_to_b(self) -> int:
        """Entities with a non-NaN median_gap_a_to_nearest_b."""
        return int(self._data["median_gap_a_to_nearest_b"].notna().sum())

    @property
    def n_with_gap_b_to_a(self) -> int:
        """Entities with a non-NaN median_gap_b_to_nearest_a."""
        return int(self._data["median_gap_b_to_nearest_a"].notna().sum())

    # ------------------------------------------------------------------ #
    # Properties — cohort-level gap summaries
    # ------------------------------------------------------------------ #

    @property
    def cohort_median_gap_a_to_b(self) -> float:
        """
        Median of per-entity median_gap_a_to_nearest_b across the cohort.
        NaN if no entities have a gap observation.
        """
        vals = self._data["median_gap_a_to_nearest_b"].dropna()
        if vals.empty:
            return float("nan")
        return round(float(vals.median()), 1)

    @property
    def cohort_median_gap_b_to_a(self) -> float:
        """
        Median of per-entity median_gap_b_to_nearest_a across the cohort.
        NaN if no entities have a gap observation.
        """
        vals = self._data["median_gap_b_to_nearest_a"].dropna()
        if vals.empty:
            return float("nan")
        return round(float(vals.median()), 1)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100 * x / n, 1)}%)" if n else str(x)

        def fmt(v):
            return f"{v} days" if not math.isnan(v) else "NaN"

        return (
            f"EventCoOccurrenceGapSummary:\n"
            f"  identity_a               : {self._identity_a}\n"
            f"  identity_b               : {self._identity_b}\n"
            f"  entity_col               : {self._entity_col}\n"
            f"  entities                 : {n:,}\n"
            f"  {'─' * 44}\n"
            f"  n_co_occurring           : {pct(self.n_co_occurring)}\n"
            f"  n_with_gap_a_to_b        : {pct(self.n_with_gap_a_to_b)}\n"
            f"  n_with_gap_b_to_a        : {pct(self.n_with_gap_b_to_a)}\n"
            f"  {'─' * 44}\n"
            f"  cohort_median_a_to_b     : {fmt(self.cohort_median_gap_a_to_b)}\n"
            f"  cohort_median_b_to_a     : {fmt(self.cohort_median_gap_b_to_a)}\n"
        )
