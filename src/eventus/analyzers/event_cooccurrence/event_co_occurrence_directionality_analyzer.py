"""
event_co_occurrence_directionality_analyzer.py
EventCoOccurrenceDirectionalityAnalyzer — statistical test comparing
the observed distribution of mean signed gaps to a permutation null.

Takes an EventCoOccurrenceDirectionalitySummary and produces an
EventCoOccurrenceDirectionalityTest.

This is a second-level analyzer — takes an intermediate result as
input rather than a CohortTimeline.

Permutation null
----------------
For each permutation, for each co-occurring entity:
  - Draw n_a new A dates uniformly from [obs_start, obs_end]
  - Draw n_b new B dates uniformly from [obs_start, obs_end]
  - Recompute mean signed gap
  - Record whether mean signed gap > 0 (A first)

The null fraction_a_first is computed empirically — not assumed to
be 0.50. For patients with many events, the null fraction may deviate
from 0.50 depending on event count and observation window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_summary import (
    EventCoOccurrenceDirectionalitySummary,
)

_ERROR = "[EventCoOccurrenceDirectionalityAnalyzer] Error"


def _permutation_signed_gaps_for_entity(
    n_a:            int,
    n_b:            int,
    obs_length:     float,
    n_permutations: int,
    rng:            np.random.Generator,
) -> np.ndarray:
    """
    Vectorized permutation mean signed gaps for one entity.

    Returns array of shape (n_permutations,) — one mean signed gap
    per permutation. NaN if n_a=0, n_b=0, or obs_length=0.
    """
    if n_a == 0 or n_b == 0 or obs_length <= 0:
        return np.full(n_permutations, np.nan)

    # Draw random dates
    a_dates = rng.uniform(0, obs_length, size=(n_permutations, n_a))
    b_dates = rng.uniform(0, obs_length, size=(n_permutations, n_b))

    # Signed differences: (n_permutations, n_a, n_b)
    # Positive = B after A
    diff = b_dates[:, np.newaxis, :] - a_dates[:, :, np.newaxis]

    # For each A, find nearest B by absolute distance
    abs_diff  = np.abs(diff)
    nearest_idx = abs_diff.argmin(axis=2)   # (n_permutations, n_a)

    # Gather signed gap for nearest B
    perm_idx   = np.arange(n_permutations)[:, np.newaxis]
    a_idx      = np.arange(n_a)[np.newaxis, :]
    signed     = diff[perm_idx, a_idx, nearest_idx]   # (n_permutations, n_a)

    # Mean across A events → (n_permutations,)
    return signed.mean(axis=1)


class EventCoOccurrenceDirectionalityAnalyzer:
    """
    Statistical test comparing the observed mean signed gap distribution
    to a permutation-based null.

    Parameters
    ----------
    directionality_summary : EventCoOccurrenceDirectionalitySummary

    Examples
    --------
    >>> directionality  = analyzer.compute_directionality()
    >>> dir_analyzer    = EventCoOccurrenceDirectionalityAnalyzer(directionality)
    >>> dir_test        = dir_analyzer.compute_test(n_permutations=500)
    >>> print(dir_test)
    """

    _summary: EventCoOccurrenceDirectionalitySummary

    def __init__(
        self,
        directionality_summary: EventCoOccurrenceDirectionalitySummary,
    ) -> None:
        if not isinstance(directionality_summary, EventCoOccurrenceDirectionalitySummary):
            raise TypeError(
                f"{_ERROR}: directionality_summary must be an "
                f"EventCoOccurrenceDirectionalitySummary, "
                f"got {type(directionality_summary).__name__}"
            )
        if directionality_summary.n_co_occurring == 0:
            raise ValueError(
                f"{_ERROR}: no co-occurring entities. Cannot compute test."
            )
        self._summary = directionality_summary

    @property
    def directionality_summary(self) -> EventCoOccurrenceDirectionalitySummary:
        return self._summary

    def compute_test(
        self,
        n_permutations: int = 500,
        seed:           int = 42,
    ) -> "EventCoOccurrenceDirectionalityTest":
        """
        Compare the observed mean signed gap distribution to a
        permutation null using the Wilcoxon signed-rank test.

        Parameters
        ----------
        n_permutations : int — default 500
        seed           : int — random seed for reproducibility

        Returns
        -------
        EventCoOccurrenceDirectionalityTest
        """
        from scipy.stats import wilcoxon

        from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_test import (
            EventCoOccurrenceDirectionalityTest,
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

        # ── Observed signed gaps ──────────────────────────────────────────
        obs = co_occ["mean_signed_gap"].values
        obs_clean = obs[~np.isnan(obs)]

        # ── Permutation null ──────────────────────────────────────────────
        null_list = []
        for i in range(len(co_occ)):
            perm = _permutation_signed_gaps_for_entity(
                n_a_vals[i], n_b_vals[i], obs_lengths[i], n_permutations, rng
            )
            null_list.append(perm)

        null_all   = np.concatenate(null_list)
        null_clean = null_all[~np.isnan(null_all)]

        # ── Fraction A first ──────────────────────────────────────────────
        obs_nontied   = obs_clean[obs_clean != 0]
        frac_a_first  = float((obs_nontied > 0).sum() / len(obs_nontied)) if len(obs_nontied) else float("nan")

        null_nontied          = null_clean[null_clean != 0]
        null_frac_a_first     = float((null_nontied > 0).sum() / len(null_nontied)) if len(null_nontied) else float("nan")

        # ── Wilcoxon signed-rank test ─────────────────────────────────────
        # Tests whether observed signed gaps are symmetric around zero
        # Uses only non-zero observed values (ties excluded per convention)
        if len(obs_nontied) < 10:
            wstat, wp = float("nan"), float("nan")
        else:
            result = wilcoxon(obs_nontied, alternative="two-sided")
            wstat, wp = float(result.statistic), float(result.pvalue)

        return EventCoOccurrenceDirectionalityTest(
            identity_a            = self._summary.identity_a,
            identity_b            = self._summary.identity_b,
            n_entities            = self._summary.n_entities,
            n_co_occurring        = self._summary.n_co_occurring,
            n_permutations        = n_permutations,
            observed_signed_gaps  = obs_clean,
            null_signed_gaps      = null_clean,
            fraction_a_first      = frac_a_first,
            null_fraction_a_first = null_frac_a_first,
            wilcoxon_statistic    = wstat,
            wilcoxon_p            = wp,
        )

    def __repr__(self) -> str:
        return (
            f"EventCoOccurrenceDirectionalityAnalyzer(\n"
            f"  identity_a     : '{self._summary.identity_a}'\n"
            f"  identity_b     : '{self._summary.identity_b}'\n"
            f"  n_co_occurring : {self._summary.n_co_occurring:,}\n"
            f")"
        )
