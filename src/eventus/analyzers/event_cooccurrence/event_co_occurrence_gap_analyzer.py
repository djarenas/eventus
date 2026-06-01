"""
event_co_occurrence_gap_analyzer.py
EventCoOccurrenceGapAnalyzer — statistical test comparing observed
gap distribution to a permutation-based null.

Takes an EventCoOccurrenceGapSummary (per-entity gaps) and produces
an EventCoOccurrenceGapTest (cohort-level KS test result).

This is a second-level analyzer — it takes an intermediate result
as input rather than a CohortTimeline.

Permutation null
----------------
For each permutation, for each co-occurring entity:
  - Draw n_a new A dates uniformly from [obs_start, obs_end]
  - Draw n_b new B dates uniformly from [obs_start, obs_end]
  - Recompute nearest gap A→B and B→A
  - Take median across A events (and B events for reverse direction)

This preserves each entity's event counts and observation window
while destroying any temporal relationship between A and B.
The inner loop is fully vectorized with numpy.

Design notes (future expansion)
---------------------------------
- No config accepted for now. Future version will accept a config
  controlling n_permutations and summary statistic (median vs mean).
"""
from __future__ import annotations

import numpy as np

from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_summary import (
    EventCoOccurrenceGapSummary,
)

_ERROR = "[EventCoOccurrenceGapAnalyzer] Error"


def _permutation_gaps_for_entity(
    n_a:            int,
    n_b:            int,
    obs_length:     float,
    n_permutations: int,
    rng:            np.random.Generator,
) -> np.ndarray:
    """
    Vectorized permutation gaps for one entity.

    For each of n_permutations permutations, draws n_a and n_b dates
    uniformly from [0, obs_length], computes nearest gap from each A
    to nearest B, takes median across A events.

    Returns
    -------
    np.ndarray of shape (n_permutations,)
        One median gap per permutation. NaN if n_a=0, n_b=0, or
        obs_length=0.
    """
    if n_a == 0 or n_b == 0 or obs_length <= 0:
        return np.full(n_permutations, np.nan)

    # Draw random dates
    # a_dates: (n_permutations, n_a)
    # b_dates: (n_permutations, n_b)
    a_dates = rng.uniform(0, obs_length, size=(n_permutations, n_a))
    b_dates = rng.uniform(0, obs_length, size=(n_permutations, n_b))

    # Absolute differences: (n_permutations, n_a, n_b)
    diff = np.abs(
        a_dates[:, :, np.newaxis] - b_dates[:, np.newaxis, :]
    )

    # Nearest B for each A: min over B axis → (n_permutations, n_a)
    nearest = diff.min(axis=2)

    # Median over A axis → (n_permutations,)
    return np.median(nearest, axis=1)


class EventCoOccurrenceGapAnalyzer:
    """
    Statistical test comparing the observed gap distribution in an
    EventCoOccurrenceGapSummary to a permutation-based null.

    For each permutation both A and B event dates are shuffled
    uniformly within each entity's observation period. This preserves
    event counts and observation windows while destroying any temporal
    relationship between A and B.

    Parameters
    ----------
    gap_summary : EventCoOccurrenceGapSummary
        Per-entity gap statistics from EventCoOccurrenceAnalyzer.compute_gaps().

    Raises
    ------
    TypeError
        If gap_summary is not an EventCoOccurrenceGapSummary.
    ValueError
        If no co-occurring entities exist in the summary.

    Examples
    --------
    >>> gaps     = analyzer.compute_gaps()
    >>> gap_test = EventCoOccurrenceGapAnalyzer(gaps).compute_test(
    ...     n_permutations=500
    ... )
    >>> print(gap_test)
    """

    _summary: EventCoOccurrenceGapSummary

    def __init__(self, gap_summary: EventCoOccurrenceGapSummary) -> None:
        if not isinstance(gap_summary, EventCoOccurrenceGapSummary):
            raise TypeError(
                f"{_ERROR}: gap_summary must be an EventCoOccurrenceGapSummary, "
                f"got {type(gap_summary).__name__}"
            )
        if gap_summary.n_co_occurring == 0:
            raise ValueError(
                f"{_ERROR}: gap_summary has no co-occurring entities. "
                f"Cannot compute gap test."
            )
        self._summary = gap_summary

    @property
    def gap_summary(self) -> EventCoOccurrenceGapSummary:
        return self._summary

    def compute_test(
        self,
        n_permutations: int = 500,
        seed:           int = 42,
    ) -> "EventCoOccurrenceGapTest":
        """
        Compare the observed gap distribution to a permutation null.

        For each permutation, A and B dates are shuffled uniformly
        within each entity's observation period. The KS test compares
        the observed per-entity median gaps to the pooled permutation
        null distribution.

        Parameters
        ----------
        n_permutations : int
            Number of permutations. Default 500. Increase to 1000 for
            more stable null estimates.
        seed : int
            Random seed for reproducibility.

        Returns
        -------
        EventCoOccurrenceGapTest
        """
        import pandas as pd
        from scipy.stats import ks_2samp

        from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_test import (
            EventCoOccurrenceGapTest,
        )

        if not isinstance(n_permutations, int) or n_permutations < 1:
            raise ValueError(
                f"{_ERROR}: n_permutations must be a positive integer, "
                f"got {n_permutations!r}"
            )

        rng  = np.random.default_rng(seed)
        data = self._summary.data

        # ── Filter to co-occurring entities ──────────────────────────────
        co_occ = data[
            (data["n_a"] > 0) & (data["n_b"] > 0)
        ].copy().reset_index(drop=True)

        obs_lengths = (
            pd.to_datetime(co_occ["obs_end"]) -
            pd.to_datetime(co_occ["obs_start"])
        ).dt.days.astype(float).values

        n_a_vals = co_occ["n_a"].values.astype(int)
        n_b_vals = co_occ["n_b"].values.astype(int)

        # ── Observed gaps ─────────────────────────────────────────────────
        obs_a_to_b = co_occ["median_gap_a_to_nearest_b"].values
        obs_b_to_a = co_occ["median_gap_b_to_nearest_a"].values

        # ── Permutation null ──────────────────────────────────────────────
        # For each entity, generate n_permutations shuffled median gaps
        # A→B direction uses n_a, n_b
        # B→A direction uses n_b, n_a (source and target swapped)
        null_a_to_b_list = []
        null_b_to_a_list = []

        for i in range(len(co_occ)):
            # A→B: shuffle n_a A dates and n_b B dates
            perm_ab = _permutation_gaps_for_entity(
                n_a_vals[i], n_b_vals[i], obs_lengths[i], n_permutations, rng
            )
            null_a_to_b_list.append(perm_ab)

            # B→A: shuffle n_b B dates and n_a A dates (source = B)
            perm_ba = _permutation_gaps_for_entity(
                n_b_vals[i], n_a_vals[i], obs_lengths[i], n_permutations, rng
            )
            null_b_to_a_list.append(perm_ba)

        # Pool across all entities and permutations
        null_a_to_b = np.concatenate(null_a_to_b_list)
        null_b_to_a = np.concatenate(null_b_to_a_list)

        # Remove NaN
        mask_ab = ~np.isnan(obs_a_to_b) & True
        mask_ba = ~np.isnan(obs_b_to_a) & True
        null_ab_clean = null_a_to_b[~np.isnan(null_a_to_b)]
        null_ba_clean = null_b_to_a[~np.isnan(null_b_to_a)]

        # ── KS tests ──────────────────────────────────────────────────────
        ks_stat_ab, ks_p_ab = ks_2samp(
            obs_a_to_b[mask_ab], null_ab_clean
        )
        ks_stat_ba, ks_p_ba = ks_2samp(
            obs_b_to_a[mask_ba], null_ba_clean
        )

        return EventCoOccurrenceGapTest(
            identity_a           = self._summary.identity_a,
            identity_b           = self._summary.identity_b,
            n_entities           = self._summary.n_entities,
            n_co_occurring       = self._summary.n_co_occurring,
            n_permutations       = n_permutations,
            null_method          = "permutation",
            observed_gaps_a_to_b = obs_a_to_b[mask_ab],
            null_gaps_a_to_b     = null_ab_clean,
            ks_statistic_a_to_b  = ks_stat_ab,
            ks_p_a_to_b          = ks_p_ab,
            observed_gaps_b_to_a = obs_b_to_a[mask_ba],
            null_gaps_b_to_a     = null_ba_clean,
            ks_statistic_b_to_a  = ks_stat_ba,
            ks_p_b_to_a          = ks_p_ba,
        )

    def __repr__(self) -> str:
        return (
            f"EventCoOccurrenceGapAnalyzer(\n"
            f"  identity_a     : '{self._summary.identity_a}'\n"
            f"  identity_b     : '{self._summary.identity_b}'\n"
            f"  n_co_occurring : {self._summary.n_co_occurring:,}\n"
            f")"
        )
