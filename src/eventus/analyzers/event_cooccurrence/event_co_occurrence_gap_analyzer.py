"""
event_co_occurrence_gap_analyzer.py
EventCoOccurrenceGapAnalyzer — statistical test comparing the observed
gap distribution to a resampling-based null.

Takes an EventCoOccurrenceGapSummary (per-entity gaps) and produces
an EventCoOccurrenceGapTest (cohort-level KS test result).

This is a second-level analyzer — it takes an intermediate result
as input rather than a CohortTimeline.

Null models
-----------
Three null models are available via the ``null_method`` argument of
``compute_test``. All three operate per entity and hold each entity's
event counts and observation-window length fixed; they differ in what
temporal structure they preserve:

- "uniform_monte_carlo" (default): for each iteration, draw n_a new A dates and
  n_b new B dates uniformly over the observation period, then recompute
  the gap. Fast, but assumes each event type is uniformly (Poisson-like)
  placed — it does NOT preserve within-type clustering (burstiness), and
  can therefore read self-clustering of a single type as co-occurrence.

- "rotation": keep each type's observed dates, and for each iteration
  shift the target type's whole date sequence by a random offset within
  the window (wrapping around, mod window length). Preserves each type's
  own inter-event structure (including burstiness) exactly and breaks
  only the A–B phase relationship. This is the "random offset" model
  from the temporal-networks null-model literature.

- "label_permutation": pool each entity's observed A and B dates, then
  randomly reassign which are A and which are B (keeping the counts).
  Preserves the combined set of event times but blends the two types.

The "rotation" and "label_permutation" nulls require the per-entity
event offsets carried in the summary (columns a_offsets / b_offsets);
"uniform_monte_carlo" needs only the counts. All inner loops are vectorized
with numpy.

References
----------
Haiminen, Mannila & Terzi (2008), BMC Bioinformatics 9:336;
Gauvin et al. (2018), arXiv:1806.04032; Holme & Saramäki (2012),
Physics Reports 519:97-125.
"""
from __future__ import annotations

import numpy as np

from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_summary import (
    EventCoOccurrenceGapSummary,
)

_ERROR = "[EventCoOccurrenceGapAnalyzer] Error"


def _montecarlo_gaps_for_entity(
    n_source:   int,
    n_target:   int,
    obs_length: float,
    n_iter:     int,
    rng:        np.random.Generator,
) -> np.ndarray:
    """
    Uniform Monte Carlo median gaps for one entity, source→target.

    For each of n_iter iterations, draws n_source and n_target dates
    uniformly from [0, obs_length], computes the nearest gap from each
    source event to the nearest target event, and takes the median.

    Returns
    -------
    np.ndarray of shape (n_iter,)
        One median gap per iteration. NaN if n_source=0, n_target=0, or
        obs_length<=0.
    """
    if n_source == 0 or n_target == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)

    # Draw random dates uniformly (does NOT preserve burstiness)
    s_dates = rng.uniform(0, obs_length, size=(n_iter, n_source))
    t_dates = rng.uniform(0, obs_length, size=(n_iter, n_target))

    diff = np.abs(s_dates[:, :, np.newaxis] - t_dates[:, np.newaxis, :])
    nearest = diff.min(axis=2)                      # (n_iter, n_source)
    return np.median(nearest, axis=1)


def _rotation_gaps_for_entity(
    source_offsets: np.ndarray,
    target_offsets: np.ndarray,
    obs_length:     float,
    n_iter:         int,
    rng:            np.random.Generator,
) -> np.ndarray:
    """
    Rotation ("random offset") median gaps for one entity, source→target.

    The source dates are held fixed at their observed offsets; the target
    sequence is shifted by a random offset within [0, obs_length),
    wrapping around (mod obs_length), for each iteration. This preserves
    each type's own inter-event structure (burstiness) and randomizes only
    the A–B phase. Median nearest gap across source events is returned.
    """
    n_s = len(source_offsets)
    n_t = len(target_offsets)
    if n_s == 0 or n_t == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)

    src = np.asarray(source_offsets, dtype=float)               # (n_s,)
    tgt = np.asarray(target_offsets, dtype=float)               # (n_t,)

    shifts  = rng.uniform(0, obs_length, size=(n_iter, 1))
    tgt_rot = np.mod(tgt[np.newaxis, :] + shifts, obs_length)   # (n_iter, n_t)

    diff = np.abs(src[np.newaxis, :, np.newaxis] - tgt_rot[:, np.newaxis, :])
    nearest = diff.min(axis=2)                                  # (n_iter, n_s)
    return np.median(nearest, axis=1)


def _labelperm_gaps_for_entity(
    source_offsets: np.ndarray,
    target_offsets: np.ndarray,
    obs_length:     float,
    n_iter:         int,
    rng:            np.random.Generator,
) -> np.ndarray:
    """
    Label-permutation median gaps for one entity, source→target.

    Pools the observed source and target offsets, then for each iteration
    randomly reassigns which are "source" and which are "target" (keeping
    the counts). Preserves the combined event times and counts; blends the
    two types' individual timing. Median nearest gap across the permuted
    source events is returned.
    """
    n_s = len(source_offsets)
    n_t = len(target_offsets)
    if n_s == 0 or n_t == 0 or obs_length <= 0:
        return np.full(n_iter, np.nan)

    pool    = np.concatenate([
        np.asarray(source_offsets, dtype=float),
        np.asarray(target_offsets, dtype=float),
    ])
    n_total = n_s + n_t

    perm    = rng.random((n_iter, n_total)).argsort(axis=1)     # (n_iter, n_total)
    pooled  = pool[perm]
    src     = pooled[:, :n_s]                                   # (n_iter, n_s)
    tgt     = pooled[:, n_s:]                                   # (n_iter, n_t)

    diff = np.abs(src[:, :, np.newaxis] - tgt[:, np.newaxis, :])
    nearest = diff.min(axis=2)                                  # (n_iter, n_s)
    return np.median(nearest, axis=1)


_VALID_NULL_METHODS = ("uniform_monte_carlo", "rotation", "label_permutation")


def _gap_null_for_direction(
    null_method:    str,
    n_source:       int,
    n_target:       int,
    source_offsets, target_offsets,
    obs_length:     float,
    n_iter:         int,
    rng:            np.random.Generator,
) -> np.ndarray:
    """Dispatch to the requested null for one source→target direction."""
    if null_method == "uniform_monte_carlo":
        return _montecarlo_gaps_for_entity(n_source, n_target, obs_length, n_iter, rng)
    if null_method == "rotation":
        return _rotation_gaps_for_entity(source_offsets, target_offsets, obs_length, n_iter, rng)
    if null_method == "label_permutation":
        return _labelperm_gaps_for_entity(source_offsets, target_offsets, obs_length, n_iter, rng)
    raise ValueError(
        f"{_ERROR}: null_method must be one of {_VALID_NULL_METHODS}, got {null_method!r}"
    )


class EventCoOccurrenceGapAnalyzer:
    """
    Statistical test comparing the observed gap distribution in an
    EventCoOccurrenceGapSummary to a resampling-based null.

    Three null models are available (see module docstring and the
    ``null_method`` argument of ``compute_test``): "uniform_monte_carlo" (uniform
    placement; the default), "rotation" (preserves each type's own
    burstiness), and "label_permutation". All hold each entity's event
    counts and observation window fixed.

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
    ...     null_method="rotation", n_iterations=500
    ... )
    >>> print(gap_test)
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _summary: EventCoOccurrenceGapSummary  # per-entity gap statistics input

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
        n_iterations:   int  = 500,
        seed:           int  = 42,
        null_method:    str  = "uniform_monte_carlo",
    ) -> "EventCoOccurrenceGapTest":
        """
        Compare the observed gap distribution to a resampling null.

        The KS test compares the observed per-entity median gaps to the
        pooled null distribution generated by ``null_method``.

        Parameters
        ----------
        n_iterations : int
            Number of resampling iterations. Default 500. Increase to
            1000 for more stable null estimates.
        seed : int
            Random seed for reproducibility.
        null_method : {"uniform_monte_carlo", "rotation", "label_permutation"}
            Null model to use. Default "uniform_monte_carlo" (uniform placement).
            "rotation" and "label_permutation" require the per-entity
            a_offsets / b_offsets columns produced by compute_gaps().

        Returns
        -------
        EventCoOccurrenceGapTest
        """
        import pandas as pd
        from scipy.stats import ks_2samp

        from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_test import (
            EventCoOccurrenceGapTest,
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

        # Per-entity offsets are required for rotation / label_permutation.
        needs_offsets = null_method in ("rotation", "label_permutation")
        if needs_offsets and not {"a_offsets", "b_offsets"}.issubset(co_occ.columns):
            raise ValueError(
                f"{_ERROR}: null_method={null_method!r} requires per-entity "
                f"a_offsets / b_offsets, which are produced by compute_gaps(). "
                f"This summary predates offset capture; rebuild it, or use "
                f"null_method='uniform_monte_carlo'."
            )
        a_off = co_occ["a_offsets"].values if needs_offsets else [None] * len(co_occ)
        b_off = co_occ["b_offsets"].values if needs_offsets else [None] * len(co_occ)

        # ── Observed gaps ─────────────────────────────────────────────────
        obs_a_to_b = co_occ["median_gap_a_to_nearest_b"].values
        obs_b_to_a = co_occ["median_gap_b_to_nearest_a"].values

        # ── Null distribution ─────────────────────────────────────────────
        # A→B direction: source = A, target = B
        # B→A direction: source = B, target = A (source and target swapped)
        null_a_to_b_list = []
        null_b_to_a_list = []

        for i in range(len(co_occ)):
            null_a_to_b_list.append(
                _gap_null_for_direction(
                    null_method,
                    n_a_vals[i], n_b_vals[i],
                    a_off[i], b_off[i],
                    obs_lengths[i], n_iter, rng,
                )
            )
            null_b_to_a_list.append(
                _gap_null_for_direction(
                    null_method,
                    n_b_vals[i], n_a_vals[i],
                    b_off[i], a_off[i],
                    obs_lengths[i], n_iter, rng,
                )
            )

        # Pool across all entities and iterations
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
            n_iterations       = n_iter,
            null_method          = null_method,
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
