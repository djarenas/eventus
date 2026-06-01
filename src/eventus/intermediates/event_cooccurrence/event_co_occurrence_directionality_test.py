"""
event_co_occurrence_directionality_test.py
EventCoOccurrenceDirectionalityTest — cohort-level directionality test.

Produced by
-----------
EventCoOccurrenceDirectionalityAnalyzer.compute_test()

Compares the observed distribution of per-entity mean signed gaps to
a permutation-based null using the Wilcoxon signed-rank test.
"""
from __future__ import annotations
import math
import numpy as np

_ERROR = "[EventCoOccurrenceDirectionalityTest] Error"

_WILCOXON_NOTE = (
    "Wilcoxon signed-rank test comparing per-entity mean signed gaps "
    "to zero under a permutation null. Both A and B event dates are "
    "shuffled independently for each entity in each permutation, "
    "preserving event counts and observation windows. A significant "
    "result means the distribution of signed gaps differs from what "
    "independence would produce — typically positive values indicate "
    "A tends to precede B. Does not describe mechanisms or confirm "
    "causality. See ch8-12_simulation_design.md for statistical "
    "disclaimer."
)


class EventCoOccurrenceDirectionalityTest:
    """
    Cohort-level directionality test for two event identities.

    Produced by
    -----------
    EventCoOccurrenceDirectionalityAnalyzer.compute_test()

    Parameters
    ----------
    identity_a              : str
    identity_b              : str
    n_entities              : int
    n_co_occurring          : int
    n_permutations          : int
    observed_signed_gaps    : np.ndarray — per-entity mean signed gaps
    null_signed_gaps        : np.ndarray — pooled permutation null gaps
    fraction_a_first        : float — observed fraction with gap > 0
    null_fraction_a_first   : float — null fraction with gap > 0
    wilcoxon_statistic      : float
    wilcoxon_p              : float
    """

    def __init__(
        self,
        identity_a:            str,
        identity_b:            str,
        n_entities:            int,
        n_co_occurring:        int,
        n_permutations:        int,
        observed_signed_gaps:  np.ndarray,
        null_signed_gaps:      np.ndarray,
        fraction_a_first:      float,
        null_fraction_a_first: float,
        wilcoxon_statistic:    float,
        wilcoxon_p:            float,
    ) -> None:
        for name, val in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(f"{_ERROR}: {name} must be a non-empty string.")
        if identity_a == identity_b:
            raise ValueError(f"{_ERROR}: identity_a and identity_b must differ.")
        if n_co_occurring == 0:
            raise ValueError(
                f"{_ERROR}: n_co_occurring is 0. Cannot compute directionality test."
            )

        self._identity_a            = identity_a
        self._identity_b            = identity_b
        self._n_entities            = n_entities
        self._n_co_occurring        = n_co_occurring
        self._n_permutations        = n_permutations
        self._observed              = np.asarray(observed_signed_gaps, dtype=float)
        self._null                  = np.asarray(null_signed_gaps,     dtype=float)
        self._fraction_a_first      = float(fraction_a_first)
        self._null_fraction_a_first = float(null_fraction_a_first)
        self._wilcoxon_stat         = float(wilcoxon_statistic)
        self._wilcoxon_p            = float(wilcoxon_p)

    # ------------------------------------------------------------------ #
    # Properties
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

    @property
    def n_permutations(self) -> int:
        return self._n_permutations

    @property
    def observed_signed_gaps(self) -> np.ndarray:
        return self._observed.copy()

    @property
    def null_signed_gaps(self) -> np.ndarray:
        return self._null.copy()

    @property
    def fraction_a_first(self) -> float:
        return self._fraction_a_first

    @property
    def null_fraction_a_first(self) -> float:
        return self._null_fraction_a_first

    @property
    def wilcoxon_statistic(self) -> float:
        return self._wilcoxon_stat

    @property
    def wilcoxon_p(self) -> float:
        return self._wilcoxon_p

    @property
    def direction_ratio(self) -> float:
        """
        fraction_a_first / null_fraction_a_first.
        Values > 1 mean A precedes B more than independence predicts.
        Values ≈ 1 mean no directional signal.
        """
        if math.isnan(self._null_fraction_a_first) or self._null_fraction_a_first == 0:
            return float("nan")
        return round(self._fraction_a_first / self._null_fraction_a_first, 3)

    @property
    def wilcoxon_note(self) -> str:
        return _WILCOXON_NOTE

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def _fmt_p(self, p: float) -> str:
        if math.isnan(p):
            return "NaN"
        if p < 0.001:
            return f"{p:.2e}"
        return f"{p:.4f}"

    def __repr__(self) -> str:
        n  = self._n_entities
        nc = self._n_co_occurring

        obs_clean = self._observed[~np.isnan(self._observed)]
        obs_mean  = f"{float(np.mean(obs_clean)):.1f} days" if len(obs_clean) else "NaN"
        null_clean = self._null[~np.isnan(self._null)]
        null_mean  = f"{float(np.mean(null_clean)):.1f} days" if len(null_clean) else "NaN"

        return (
            f"EventCoOccurrenceDirectionalityTest:\n"
            f"  identity_a             : {self._identity_a}\n"
            f"  identity_b             : {self._identity_b}\n"
            f"  entities               : {n:,}\n"
            f"  n_co_occurring         : {nc:,} ({round(100*nc/n,1)}%)\n"
            f"  null_method            : permutation (n_permutations={self._n_permutations:,})\n"
            f"  {'─' * 50}\n"
            f"  fraction_a_first       : {round(self._fraction_a_first*100,1)}%\n"
            f"  null_fraction_a_first  : {round(self._null_fraction_a_first*100,1)}%\n"
            f"  direction_ratio        : {self.direction_ratio}  (observed/null)\n"
            f"  {'─' * 50}\n"
            f"  cohort_mean_signed_gap : {obs_mean}\n"
            f"  null_mean_signed_gap   : {null_mean}\n"
            f"  wilcoxon_statistic     : {self._wilcoxon_stat:.4f}\n"
            f"  wilcoxon_p             : {self._fmt_p(self._wilcoxon_p)}\n"
        )
