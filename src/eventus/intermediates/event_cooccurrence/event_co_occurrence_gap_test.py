"""
event_co_occurrence_gap_test.py
EventCoOccurrenceGapTest — cohort-level gap distribution test comparing
observed gaps to an analytical null.

Produced by
-----------
EventCoOccurrenceGapAnalyzer.compute_test()

This object answers: are the observed gaps between A and B events
shorter than chance would predict given the number of events and the
observation window?

The analytical null
-------------------
For each co-occurring entity i, the expected median gap is:

    expected_gap_i = obs_length_i / (2 * (n_b_i + 1))   [A→nearest B]
    expected_gap_i = obs_length_i / (2 * (n_a_i + 1))   [B→nearest A]

This is the expected nearest-neighbor distance when B events are placed
uniformly and independently in the observation period. It respects each
entity's individual event count and observation window.

The KS test
-----------
scipy.stats.ks_2samp compares the observed gap distribution to the
analytical null distribution. A significant result means observed gaps
are distributed differently from what independence would predict —
typically shorter (signal) rather than longer.

Design notes (future expansion)
---------------------------------
- Analytical null assumes uniform B placement. A permutation-based null
  (shuffle B dates N times) makes no distributional assumption and will
  be available in a future version via analyzer config.
- Median gap per entity chosen over all individual gaps — see
  EventCoOccurrenceGapSummary docstring.
"""
from __future__ import annotations
import math
import numpy as np

_ERROR = "[EventCoOccurrenceGapTest] Error"

_KS_NOTE = (
    "Two-sample KS test comparing observed per-entity median gaps to a "
    "permutation-based null. For each permutation both A and B event dates "
    "are shuffled uniformly within each entity's observation period, "
    "preserving event counts. A significant result means observed gaps differ "
    "from what independence would produce — typically shorter gaps indicate "
    "temporal clustering. Does not describe mechanisms or directionality."
)


class EventCoOccurrenceGapTest:
    """
    Cohort-level gap distribution test for two event identities.

    Produced by
    -----------
    EventCoOccurrenceGapAnalyzer.compute_test()

    Parameters
    ----------
    identity_a            : str
    identity_b            : str
    n_entities            : int — total cohort size
    n_co_occurring        : int — entities with both n_a > 0 and n_b > 0
    observed_gaps_a_to_b  : np.ndarray — per-entity median gap, A→nearest B
    null_gaps_a_to_b      : np.ndarray — analytical expected gap, A→nearest B
    ks_statistic_a_to_b   : float
    ks_p_a_to_b           : float
    observed_gaps_b_to_a  : np.ndarray — per-entity median gap, B→nearest A
    null_gaps_b_to_a      : np.ndarray — analytical expected gap, B→nearest A
    ks_statistic_b_to_a   : float
    ks_p_b_to_a           : float
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _identity_a:           str
    _identity_b:           str
    _n_entities:           int
    _n_co_occurring:       int
    _observed_a_to_b:      np.ndarray
    _null_a_to_b:          np.ndarray
    _ks_stat_a_to_b:       float
    _ks_p_a_to_b:          float
    _observed_b_to_a:      np.ndarray
    _null_b_to_a:          np.ndarray
    _ks_stat_b_to_a:       float
    _ks_p_b_to_a:          float
    _n_permutations:       int
    _null_method:          str

    def __init__(
        self,
        identity_a:           str,
        identity_b:           str,
        n_entities:           int,
        n_co_occurring:       int,
        observed_gaps_a_to_b: np.ndarray,
        null_gaps_a_to_b:     np.ndarray,
        ks_statistic_a_to_b:  float,
        ks_p_a_to_b:          float,
        observed_gaps_b_to_a: np.ndarray,
        null_gaps_b_to_a:     np.ndarray,
        ks_statistic_b_to_a:  float,
        ks_p_b_to_a:          float,
        n_permutations:       int = 0,
        null_method:          str = "analytical",
    ) -> None:
        for name, val in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(f"{_ERROR}: {name} must be a non-empty string.")
        if identity_a == identity_b:
            raise ValueError(f"{_ERROR}: identity_a and identity_b must differ.")
        if n_co_occurring == 0:
            raise ValueError(
                f"{_ERROR}: n_co_occurring is 0 — no entities had both "
                f"A and B events. Cannot compute gap test."
            )

        self._identity_a      = identity_a
        self._identity_b      = identity_b
        self._n_entities      = n_entities
        self._n_co_occurring  = n_co_occurring
        self._observed_a_to_b = np.asarray(observed_gaps_a_to_b, dtype=float)
        self._null_a_to_b     = np.asarray(null_gaps_a_to_b,     dtype=float)
        self._ks_stat_a_to_b  = float(ks_statistic_a_to_b)
        self._ks_p_a_to_b     = float(ks_p_a_to_b)
        self._observed_b_to_a = np.asarray(observed_gaps_b_to_a, dtype=float)
        self._null_b_to_a     = np.asarray(null_gaps_b_to_a,     dtype=float)
        self._ks_stat_b_to_a  = float(ks_statistic_b_to_a)
        self._ks_p_b_to_a     = float(ks_p_b_to_a)
        self._n_permutations  = n_permutations
        self._null_method     = null_method

    # ------------------------------------------------------------------ #
    # Properties — identities
    # ------------------------------------------------------------------ #

    @property
    def identity_a(self) -> str:
        return self._identity_a

    @property
    def identity_b(self) -> str:
        return self._identity_b

    @property
    def n_entities(self) -> int:
        return self._n_entities

    @property
    def n_co_occurring(self) -> int:
        return self._n_co_occurring

    # ------------------------------------------------------------------ #
    # Properties — A→B direction
    # ------------------------------------------------------------------ #

    @property
    def observed_gaps_a_to_b(self) -> np.ndarray:
        """Per-entity observed median gap, A→nearest B. Length = n_co_occurring."""
        return self._observed_a_to_b.copy()

    @property
    def null_gaps_a_to_b(self) -> np.ndarray:
        """Per-entity analytical expected gap, A→nearest B. Length = n_co_occurring."""
        return self._null_a_to_b.copy()

    @property
    def ks_statistic_a_to_b(self) -> float:
        return self._ks_stat_a_to_b

    @property
    def ks_p_a_to_b(self) -> float:
        return self._ks_p_a_to_b

    # ------------------------------------------------------------------ #
    # Properties — B→A direction
    # ------------------------------------------------------------------ #

    @property
    def observed_gaps_b_to_a(self) -> np.ndarray:
        """Per-entity observed median gap, B→nearest A. Length = n_co_occurring."""
        return self._observed_b_to_a.copy()

    @property
    def null_gaps_b_to_a(self) -> np.ndarray:
        """Per-entity analytical expected gap, B→nearest A. Length = n_co_occurring."""
        return self._null_b_to_a.copy()

    @property
    def ks_statistic_b_to_a(self) -> float:
        return self._ks_stat_b_to_a

    @property
    def ks_p_b_to_a(self) -> float:
        return self._ks_p_b_to_a

    # ------------------------------------------------------------------ #
    # Properties — notes
    # ------------------------------------------------------------------ #

    @property
    def n_permutations(self) -> int:
        return self._n_permutations

    @property
    def null_method(self) -> str:
        """'permutation' or 'analytical'."""
        return self._null_method

    @property
    def gap_ratio_a_to_b(self) -> float:
        """
        Ratio of observed median gap to null median gap, A→nearest B.
        Values < 1 mean observed gaps are shorter than the null predicts
        — temporal clustering. Values ≈ 1 mean no temporal signal.
        NaN if either distribution is empty.
        """
        obs_clean  = self._observed_a_to_b[~np.isnan(self._observed_a_to_b)]
        null_clean = self._null_a_to_b[~np.isnan(self._null_a_to_b)]
        if len(obs_clean) == 0 or len(null_clean) == 0:
            return float("nan")
        null_med = float(np.median(null_clean))
        if null_med == 0:
            return float("nan")
        return round(float(np.median(obs_clean)) / null_med, 3)

    @property
    def gap_ratio_b_to_a(self) -> float:
        """
        Ratio of observed median gap to null median gap, B→nearest A.
        Values < 1 mean observed gaps are shorter than the null predicts.
        NaN if either distribution is empty.
        """
        obs_clean  = self._observed_b_to_a[~np.isnan(self._observed_b_to_a)]
        null_clean = self._null_b_to_a[~np.isnan(self._null_b_to_a)]
        if len(obs_clean) == 0 or len(null_clean) == 0:
            return float("nan")
        null_med = float(np.median(null_clean))
        if null_med == 0:
            return float("nan")
        return round(float(np.median(obs_clean)) / null_med, 3)

    @property
    def ks_note(self) -> str:
        return _KS_NOTE

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def _fmt_p(self, p: float) -> str:
        if math.isnan(p):
            return "NaN"
        if p < 0.001:
            return f"{p:.2e}"
        return f"{p:.4f}"

    def _fmt_median(self, arr: np.ndarray) -> str:
        vals = arr[~np.isnan(arr)]
        if len(vals) == 0:
            return "NaN"
        return f"{float(np.median(vals)):.1f} days"

    def __repr__(self) -> str:
        n  = self._n_entities
        nc = self._n_co_occurring

        return (
            f"EventCoOccurrenceGapTest:\n"
            f"  identity_a             : {self._identity_a}\n"
            f"  identity_b             : {self._identity_b}\n"
            f"  entities               : {n:,}\n"
            f"  n_co_occurring         : {nc:,} ({round(100*nc/n,1)}%)\n"
            f"  null_method            : {self._null_method}"
            + (f" (n_permutations={self._n_permutations})" if self._n_permutations > 0 else "") + "\n"
            f"  {'─' * 50}\n"
            f"  {self._identity_a} → nearest {self._identity_b}\n"
            f"  {'─' * 50}\n"
            f"  observed median gap    : {self._fmt_median(self._observed_a_to_b)}\n"
            f"  null median gap        : {self._fmt_median(self._null_a_to_b)}\n"
            f"  ks_statistic           : {self._ks_stat_a_to_b:.4f}\n"
            f"  ks_p                   : {self._fmt_p(self._ks_p_a_to_b)}\n"
            f"  gap_ratio              : {self.gap_ratio_a_to_b}  (observed/null median)\n"
            f"  {'─' * 50}\n"
            f"  {self._identity_b} → nearest {self._identity_a}\n"
            f"  {'─' * 50}\n"
            f"  observed median gap    : {self._fmt_median(self._observed_b_to_a)}\n"
            f"  null median gap        : {self._fmt_median(self._null_b_to_a)}\n"
            f"  ks_statistic           : {self._ks_stat_b_to_a:.4f}\n"
            f"  ks_p                   : {self._fmt_p(self._ks_p_b_to_a)}\n"
            f"  gap_ratio              : {self.gap_ratio_b_to_a}  (observed/null median)\n"
        )
