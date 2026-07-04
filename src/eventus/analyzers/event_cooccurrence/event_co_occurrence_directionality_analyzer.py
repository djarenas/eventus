"""
event_co_occurrence_directionality_analyzer.py
EventCoOccurrenceDirectionalityAnalyzer — statistical test comparing
the observed distribution of mean signed gaps to a resampling null.

Takes an EventCoOccurrenceDirectionalitySummary and produces an
EventCoOccurrenceDirectionalityTest.

This is a second-level analyzer — takes an intermediate result as
input rather than a CohortTimeline.

Null models
-----------
Three null models are available via the ``null_method`` argument of
``compute_test``, all holding each entity's event counts and window
fixed (see EventCoOccurrenceGapAnalyzer for the full description):

- "uniform_monte_carlo" (default): draw n_a and n_b dates uniformly; recompute
  the mean signed gap. Assumes uniform placement (no burstiness).
- "rotation": keep observed dates, shift B by a random within-window
  offset (wrapping); preserves each type's own burstiness.
- "label_permutation": pool the observed A and B dates and reassign
  labels, keeping counts.

The null fraction_a_first is computed empirically — not assumed to be
0.50. "rotation" and "label_permutation" require the per-entity offsets
carried in the summary (a_offsets / b_offsets).

References
----------
Haiminen, Mannila & Terzi (2008), BMC Bioinformatics 9:336;
Gauvin et al. (2018), arXiv:1806.04032; Holme & Saramäki (2012),
Physics Reports 519:97-125.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_summary import (
    EventCoOccurrenceDirectionalitySummary,
)

_ERROR = "[EventCoOccurrenceDirectionalityAnalyzer] Error"


def _signed_from_positions(
    a: np.ndarray,   # (n_iter, n_a)
    b: np.ndarray,   # (n_iter, n_b)
) -> np.ndarray:
    """
    Mean signed gap per iteration from A/B position arrays.

    For each A event, the nearest B (by absolute distance) is found and
    its signed offset (positive = B after A) recorded; the mean across A
    events is returned. Shapes: a=(n_iter, n_a), b=(n_iter, n_b) →
    returns (n_iter,).
    """
    n_iter, n_a = a.shape
    diff        = b[:, np.newaxis, :] - a[:, :, np.newaxis]   # (n_iter, n_a, n_b)
    abs_diff    = np.abs(diff)
    nearest_idx = abs_diff.argmin(axis=2)                     # (n_iter, n_a)

    it_idx = np.arange(n_iter)[:, np.newaxis]
    a_idx  = np.arange(n_a)[np.newaxis, :]
    signed = diff[it_idx, a_idx, nearest_idx]                 # (n_iter, n_a)
    return signed.mean(axis=1)


def _montecarlo_signed_gaps_for_entity(
    n_a:        int,
    n_b:        int,
    obs_length: float,
    n_iter:     int,
    rng:        np.random.Generator,
) -> np.ndarray:
    """Uniform Monte Carlo mean signed gaps for one entity."""
    if n_a == 0 or n_b == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)
    a_dates = rng.uniform(0, obs_length, size=(n_iter, n_a))
    b_dates = rng.uniform(0, obs_length, size=(n_iter, n_b))
    return _signed_from_positions(a_dates, b_dates)


def _rotation_signed_gaps_for_entity(
    a_offsets:  np.ndarray,
    b_offsets:  np.ndarray,
    obs_length: float,
    n_iter:     int,
    rng:        np.random.Generator,
) -> np.ndarray:
    """
    Rotation ("random offset") mean signed gaps for one entity.

    A held fixed at observed offsets; B shifted by a random within-window
    offset (wrapping) each iteration. Preserves each type's burstiness.
    """
    n_a = len(a_offsets)
    n_b = len(b_offsets)
    if n_a == 0 or n_b == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)

    a       = np.tile(np.asarray(a_offsets, dtype=float), (n_iter, 1))   # (n_iter, n_a)
    b_obs   = np.asarray(b_offsets, dtype=float)
    shifts  = rng.uniform(0, obs_length, size=(n_iter, 1))
    b       = np.mod(b_obs[np.newaxis, :] + shifts, obs_length)          # (n_iter, n_b)
    return _signed_from_positions(a, b)


def _labelperm_signed_gaps_for_entity(
    a_offsets:  np.ndarray,
    b_offsets:  np.ndarray,
    obs_length: float,
    n_iter:     int,
    rng:        np.random.Generator,
) -> np.ndarray:
    """
    Label-permutation mean signed gaps for one entity.

    Pool observed A and B offsets, reassign labels each iteration keeping
    the counts, recompute mean signed gap.
    """
    n_a = len(a_offsets)
    n_b = len(b_offsets)
    if n_a == 0 or n_b == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)

    pool    = np.concatenate([
        np.asarray(a_offsets, dtype=float),
        np.asarray(b_offsets, dtype=float),
    ])
    n_total = n_a + n_b
    perm    = rng.random((n_iter, n_total)).argsort(axis=1)
    pooled  = pool[perm]
    a       = pooled[:, :n_a]      # (n_iter, n_a)
    b       = pooled[:, n_a:]      # (n_iter, n_b)
    return _signed_from_positions(a, b)


_VALID_NULL_METHODS = ("uniform_monte_carlo", "rotation", "label_permutation")


def _dir_null_for_entity(
    null_method: str,
    n_a:         int,
    n_b:         int,
    a_offsets, b_offsets,
    obs_length:  float,
    n_iter:      int,
    rng:         np.random.Generator,
) -> np.ndarray:
    """Dispatch to the requested directionality null for one entity."""
    if null_method == "uniform_monte_carlo":
        return _montecarlo_signed_gaps_for_entity(n_a, n_b, obs_length, n_iter, rng)
    if null_method == "rotation":
        return _rotation_signed_gaps_for_entity(a_offsets, b_offsets, obs_length, n_iter, rng)
    if null_method == "label_permutation":
        return _labelperm_signed_gaps_for_entity(a_offsets, b_offsets, obs_length, n_iter, rng)
    raise ValueError(
        f"{_ERROR}: null_method must be one of {_VALID_NULL_METHODS}, got {null_method!r}"
    )


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
    >>> dir_test        = dir_analyzer.compute_test(n_iterations=500)
    >>> print(dir_test)
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _summary: EventCoOccurrenceDirectionalitySummary  # per-entity directionality input

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
        n_iterations:   int  = 500,
        seed:           int  = 42,
        null_method:    str  = "uniform_monte_carlo",
    ) -> "EventCoOccurrenceDirectionalityTest":
        """
        Compare the observed mean signed gap distribution to a
        resampling null using the Wilcoxon signed-rank test.

        Parameters
        ----------
        n_iterations : int — default 500. Number of resampling iterations.
        seed           : int — random seed for reproducibility
        null_method    : {"uniform_monte_carlo", "rotation", "label_permutation"}
            Default "uniform_monte_carlo". "rotation" and "label_permutation"
            require the a_offsets / b_offsets columns from
            compute_directionality().

        Returns
        -------
        EventCoOccurrenceDirectionalityTest
        """
        from scipy.stats import wilcoxon

        from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_test import (
            EventCoOccurrenceDirectionalityTest,
        )

        n_iter = n_iterations
        if not isinstance(n_iter, int) or n_iter < 1:
            raise ValueError(
                f"{_ERROR}: number of iterations must be a positive integer, "
                f"got {n_iter!r}"
            )
        if null_method not in _VALID_NULL_METHODS:
            raise ValueError(
                f"{_ERROR}: null_method must be one of {_VALID_NULL_METHODS}, "
                f"got {null_method!r}"
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

        needs_offsets = null_method in ("rotation", "label_permutation")
        if needs_offsets and not {"a_offsets", "b_offsets"}.issubset(co_occ.columns):
            raise ValueError(
                f"{_ERROR}: null_method={null_method!r} requires per-entity "
                f"a_offsets / b_offsets from compute_directionality(). This "
                f"summary predates offset capture; rebuild it, or use "
                f"null_method='uniform_monte_carlo'."
            )
        a_off = co_occ["a_offsets"].values if needs_offsets else [None] * len(co_occ)
        b_off = co_occ["b_offsets"].values if needs_offsets else [None] * len(co_occ)

        # ── Observed signed gaps ──────────────────────────────────────────
        obs = co_occ["mean_signed_gap"].values
        obs_clean = obs[~np.isnan(obs)]

        # ── Null distribution ─────────────────────────────────────────────
        null_list = []
        for i in range(len(co_occ)):
            null_list.append(
                _dir_null_for_entity(
                    null_method,
                    n_a_vals[i], n_b_vals[i],
                    a_off[i], b_off[i],
                    obs_lengths[i], n_iter, rng,
                )
            )

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
            n_iterations        = n_iter,
            null_method           = null_method,
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
