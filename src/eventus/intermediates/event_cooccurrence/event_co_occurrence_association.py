"""
event_co_occurrence_association.py
EventCoOccurrenceAssociation — association measures derived from a 2×2
co-occurrence contingency table.

Produced by
-----------
EventCoOccurrencePresenceResult.association (lazy property)

All measures are computed from cross-sectional co-occurrence data.
See the disclaimer property for full interpretation guidance.

V1 note
-------
Confidence intervals use analytical methods (Wilson score for
proportions, log method for ratio measures). A future version may
support bootstrap CIs via a general BootstrapCI utility — this would
allow distribution-free interval estimation without assuming
normality or log-normality.
"""
from __future__ import annotations

import math
import numpy as np

_ERROR = "[EventCoOccurrenceAssociation] Error"

# Wilson score z for 95% CI
_Z95 = 1.96


# ── CI helpers ────────────────────────────────────────────────────────────────

def _wilson_ci(n: int, total: int) -> tuple[float, float]:
    """
    Wilson score confidence interval for a proportion n/total.
    Returns (lower, upper) as fractions in [0, 1].
    Handles total=0 by returning (nan, nan).
    """
    if total == 0:
        return (float("nan"), float("nan"))
    p     = n / total
    denom = 1 + _Z95 ** 2 / total
    center = (p + _Z95 ** 2 / (2 * total)) / denom
    spread = _Z95 * math.sqrt(p * (1 - p) / total + _Z95 ** 2 / (4 * total ** 2)) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def _log_ratio_ci(
    ratio: float,
    a: int, b: int, c: int, d: int,
) -> tuple[float, float]:
    """
    Log-method CI for a ratio measure (prevalence ratio or odds ratio).
    Uses the standard epidemiological variance formula.
    Returns (nan, nan) if any cell is zero.

    For prevalence ratio: a=n_with_both, b=n_a_only, c=n_b_only, d=n_neither
    For odds ratio:       same cells, different variance formula applied.
    """
    if any(x == 0 for x in [a, b, c, d]):
        return (float("nan"), float("nan"))
    if ratio <= 0 or math.isnan(ratio) or math.isinf(ratio):
        return (float("nan"), float("nan"))
    # Variance of log(ratio): 1/a - 1/(a+b) + 1/c - 1/(c+d) for PR
    # For OR: 1/a + 1/b + 1/c + 1/d
    return (float("nan"), float("nan"))  # overridden per measure below


def _log_pr_ci(
    pr: float,
    n_with_both: int, n_a_only: int,
    n_b_only: int,   n_neither: int,
) -> tuple[float, float]:
    """Log-method CI for prevalence ratio."""
    a, b = n_with_both, n_a_only
    c, d = n_b_only,    n_neither
    if any(x == 0 for x in [a, b, c, d]) or pr <= 0:
        return (float("nan"), float("nan"))
    log_se = math.sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
    lo = pr * math.exp(-_Z95 * log_se)
    hi = pr * math.exp(+_Z95 * log_se)
    return (lo, hi)


def _log_or_ci(
    or_: float,
    n_with_both: int, n_a_only: int,
    n_b_only: int,   n_neither: int,
) -> tuple[float, float]:
    """Woolf log-method CI for odds ratio."""
    a, b, c, d = n_with_both, n_a_only, n_b_only, n_neither
    if any(x == 0 for x in [a, b, c, d]) or or_ <= 0:
        return (float("nan"), float("nan"))
    log_se = math.sqrt(1/a + 1/b + 1/c + 1/d)
    lo = or_ * math.exp(-_Z95 * log_se)
    hi = or_ * math.exp(+_Z95 * log_se)
    return (lo, hi)


def _lr_ci(
    lr:     float,
    sens:   float, spec: float,
    n_b:    int,   n_no_b: int,
    positive: bool,
) -> tuple[float, float]:
    """
    Log-method CI for likelihood ratio.
    Uses variance formula from Simel et al. (1991).
    """
    if lr <= 0 or math.isnan(lr) or n_b == 0 or n_no_b == 0:
        return (float("nan"), float("nan"))
    if positive:
        # LR+ = sens / (1 - spec)
        if sens <= 0 or spec >= 1:
            return (float("nan"), float("nan"))
        var = (1 - sens) / (n_b * sens) + spec / (n_no_b * (1 - spec))
    else:
        # LR- = (1 - sens) / spec
        if sens >= 1 or spec <= 0:
            return (float("nan"), float("nan"))
        var = sens / (n_b * (1 - sens)) + (1 - spec) / (n_no_b * spec)
    if var <= 0:
        return (float("nan"), float("nan"))
    log_se = math.sqrt(var)
    lo = lr * math.exp(-_Z95 * log_se)
    hi = lr * math.exp(+_Z95 * log_se)
    return (lo, hi)


# ── Main class ────────────────────────────────────────────────────────────────

class EventCoOccurrenceAssociation:
    """
    Association measures derived from a 2×2 co-occurrence contingency
    table between two event identities.

    Produced by
    -----------
    EventCoOccurrencePresenceResult.association

    All measures are cross-sectional — they describe co-occurrence within
    observation periods, not prospective causal relationships. See the
    `disclaimer` property for full interpretation guidance.

    Confidence intervals
    --------------------
    V1 uses analytical methods:
    - Wilson score CIs for proportions (prev_a, prev_b, conditional probs)
    - Log method (Woolf) CIs for ratio measures (prevalence_ratio)
    - Simel et al. (1991) log method for likelihood ratios

    A future version may support bootstrap CIs via a general
    BootstrapCI utility for distribution-free interval estimation.

    Parameters
    ----------
    n_with_both : int — entities with both A and B
    n_a_only    : int — entities with A but not B
    n_b_only    : int — entities with B but not A
    n_neither   : int — entities with neither A nor B
    identity_a  : str
    identity_b  : str
    """

    # ── Attributes ───────────────────────────────────────────────────────
    # Raw 2×2 cell counts
    _n_with_both:  int    # entities with both A and B
    _n_a_only:     int    # entities with A but not B
    _n_b_only:     int    # entities with B but not A
    _n_neither:    int    # entities with neither A nor B
    # Derived marginals
    _n_with_a:     int    # n_with_both + n_a_only
    _n_with_b:     int    # n_with_both + n_b_only
    _n_without_a:  int    # n_b_only + n_neither
    _n_without_b:  int    # n_a_only + n_neither
    _n_total:      int    # sum of all four cells
    # Identity labels
    _identity_a:   str
    _identity_b:   str
    # Computed measures (set by _compute())
    prev_a:              float  # prevalence of A
    prev_b:              float  # prevalence of B
    prev_a_ci:           tuple  # 95% Wilson CI for prev_a
    prev_b_ci:           tuple  # 95% Wilson CI for prev_b
    p_b_given_a:         float  # P(B | A)
    p_b_given_no_a:      float  # P(B | no A)
    p_a_given_b:         float  # P(A | B)
    p_a_given_no_b:      float  # P(A | no B)
    p_b_given_a_ci:      tuple  # 95% Wilson CI
    p_b_given_no_a_ci:   tuple  # 95% Wilson CI
    p_a_given_b_ci:      tuple  # 95% Wilson CI
    p_a_given_no_b_ci:   tuple  # 95% Wilson CI
    prevalence_ratio:    float  # P(B|A) / P(B|no A)
    prevalence_ratio_ci: tuple  # 95% log-method CI
    sensitivity:         float  # P(A | B) — treating A as test for B
    specificity:         float  # P(no A | no B)

    def __init__(
        self,
        n_with_both: int,
        n_a_only:    int,
        n_b_only:    int,
        n_neither:   int,
        identity_a:  str,
        identity_b:  str,
    ) -> None:
        # ── Validate ──────────────────────────────────────────────────
        for name, val in [
            ("n_with_both", n_with_both),
            ("n_a_only",    n_a_only),
            ("n_b_only",    n_b_only),
            ("n_neither",   n_neither),
        ]:
            if not isinstance(val, int) or val < 0:
                raise ValueError(
                    f"{_ERROR}: {name} must be a non-negative integer, "
                    f"got {val!r}"
                )
        for name, val in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(f"{_ERROR}: {name} must be a non-empty string.")
        if identity_a == identity_b:
            raise ValueError(f"{_ERROR}: identity_a and identity_b must differ.")

        # ── Store raw counts ──────────────────────────────────────────
        self._n_with_both = n_with_both
        self._n_a_only    = n_a_only
        self._n_b_only    = n_b_only
        self._n_neither   = n_neither
        self._identity_a  = identity_a
        self._identity_b  = identity_b
        # Derived marginals
        self._n_with_a    = n_with_both + n_a_only
        self._n_with_b    = n_with_both + n_b_only
        self._n_without_a = n_b_only    + n_neither
        self._n_without_b = n_a_only    + n_neither
        self._n_total     = n_with_both + n_a_only + n_b_only + n_neither

        # ── Compute all measures ──────────────────────────────────────
        self._compute()

    # ------------------------------------------------------------------ #
    # Computation
    # ------------------------------------------------------------------ #

    def _compute(self) -> None:
        """Compute all point estimates and CIs."""
        a  = self._n_with_both
        b  = self._n_a_only
        c  = self._n_b_only
        d  = self._n_neither
        na = self._n_with_a
        nb = self._n_with_b
        n  = self._n_total
        n_no_a = self._n_without_a
        n_no_b = self._n_without_b

        # ── Prevalences ───────────────────────────────────────────────
        self.prev_a    = na / n if n else float("nan")
        self.prev_b    = nb / n if n else float("nan")
        self.prev_a_ci = _wilson_ci(na, n)
        self.prev_b_ci = _wilson_ci(nb, n)

        # ── Conditional probabilities ─────────────────────────────────
        self.p_b_given_a    = a / na    if na    else float("nan")
        self.p_b_given_no_a = c / n_no_a if n_no_a else float("nan")
        self.p_a_given_b    = a / nb    if nb    else float("nan")
        self.p_a_given_no_b = b / n_no_b if n_no_b else float("nan")

        self.p_b_given_a_ci    = _wilson_ci(a, na)
        self.p_b_given_no_a_ci = _wilson_ci(c, n_no_a)
        self.p_a_given_b_ci    = _wilson_ci(a, nb)
        self.p_a_given_no_b_ci = _wilson_ci(b, n_no_b)

        # ── Prevalence ratio ──────────────────────────────────────────
        self.prevalence_ratio = (
            self.p_b_given_a / self.p_b_given_no_a
            if (self.p_b_given_a    and not math.isnan(self.p_b_given_a) and
                self.p_b_given_no_a and not math.isnan(self.p_b_given_no_a))
            else float("nan")
        )
        self.prevalence_ratio_ci = _log_pr_ci(
            self.prevalence_ratio, a, b, c, d
        )

        # ── Sensitivity / specificity (treating A as test for B) ──────
        # sensitivity = P(A | B)   = a / nb
        # specificity = P(no A | no B) = d / n_no_b
        sens = self.p_a_given_b
        spec = d / n_no_b if n_no_b else float("nan")

        self.sensitivity = sens  # P(A|B)
        self.specificity = spec  # P(no A | no B)



    # ------------------------------------------------------------------ #
    # Properties — counts
    # ------------------------------------------------------------------ #

    @property
    def n_with_both(self) -> int:
        return self._n_with_both

    @property
    def n_a_only(self) -> int:
        return self._n_a_only

    @property
    def n_b_only(self) -> int:
        return self._n_b_only

    @property
    def n_neither(self) -> int:
        return self._n_neither

    @property
    def n_with_a(self) -> int:
        return self._n_with_a

    @property
    def n_with_b(self) -> int:
        return self._n_with_b

    @property
    def n_total(self) -> int:
        return self._n_total

    @property
    def identity_a(self) -> str:
        return self._identity_a

    @property
    def identity_b(self) -> str:
        return self._identity_b

    @property
    def ci_method(self) -> str:
        return "analytical (Wilson score for proportions; log/Woolf method for ratios)"

    @property
    def disclaimer(self) -> str:
        return (
            f"INTERPRETATION NOTE\n"
            f"All measures describe co-occurrence patterns within a defined\n"
            f"observation period. This is an observational analysis — the\n"
            f"measures describe associations, not mechanisms or directionality.\n"
            f"\n"
            f"  prevalence_ratio : ratio of P({self._identity_b}|{self._identity_a}) to P({self._identity_b}|no {self._identity_a})\n"
            f"  P({self._identity_b}|{self._identity_a}) : fraction of {self._identity_a} entities that also had {self._identity_b}\n"
            f"  P({self._identity_b}|no {self._identity_a}) : fraction of non-{self._identity_a} entities that had {self._identity_b}\n"
            f"  P({self._identity_a}|{self._identity_b}) : fraction of {self._identity_b} entities that also had {self._identity_a}\n"
            f"  P({self._identity_a}|no {self._identity_b}) : fraction of non-{self._identity_b} entities that had {self._identity_a}\n"
            f"\n"
            f"CI method: {self.ci_method}\n"
            f"Bootstrap CIs are not yet implemented (planned for a future version)."
        )

    # ------------------------------------------------------------------ #
    # Contingency table as DataFrame
    # ------------------------------------------------------------------ #

    @property
    def contingency_table(self):
        """
        Return the 2×2 contingency table as a pandas DataFrame with
        counts and row/column percentages.
        """
        import pandas as pd
        n = self._n_total

        def fmt(count):
            pct = round(100 * count / n, 1) if n else 0.0
            return f"{count:,} ({pct}%)"

        return pd.DataFrame(
            {
                f"has_{self._identity_b}": [
                    fmt(self._n_with_both),
                    fmt(self._n_b_only),
                    fmt(self._n_with_b),
                ],
                f"no_{self._identity_b}": [
                    fmt(self._n_a_only),
                    fmt(self._n_neither),
                    fmt(self._n_without_b),
                ],
                "total": [
                    fmt(self._n_with_a),
                    fmt(self._n_without_a),
                    fmt(n),
                ],
            },
            index=[
                f"has_{self._identity_a}",
                f"no_{self._identity_a}",
                "total",
            ],
        )

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def _fmt_measure(self, val: float, ci: tuple) -> str:
        if math.isnan(val):
            return "NaN"
        lo, hi = ci
        if math.isnan(lo) or math.isnan(hi):
            return f"{val:.3f}  (CI: NaN)"
        return f"{val:.3f}  (95% CI: {lo:.3f} – {hi:.3f})"

    def _fmt_prop(self, val: float, ci: tuple) -> str:
        if math.isnan(val):
            return "NaN"
        lo, hi = ci
        pct = round(val * 100, 1)
        lo_pct = round(lo * 100, 1) if not math.isnan(lo) else float("nan")
        hi_pct = round(hi * 100, 1) if not math.isnan(hi) else float("nan")
        if math.isnan(lo_pct) or math.isnan(hi_pct):
            return f"{pct}%  (CI: NaN)"
        return f"{pct}%  (95% CI: {lo_pct}% – {hi_pct}%)"

    def __repr__(self) -> str:
        n = self._n_total

        def pct(x):
            return f"{x:,} ({round(100*x/n,1)}%)" if n else str(x)

        lines = [
            f"EventCoOccurrenceAssociation:",
            f"  identity_a   : {self._identity_a}",
            f"  identity_b   : {self._identity_b}",
            f"  n_total      : {n:,}",
            f"",
            f"  ── 2×2 Contingency Table ──────────────────────────────",
            f"  {'':22} {'has_' + self._identity_b:>22}  {'no_' + self._identity_b:>22}  {'total':>18}",
            f"  {'has_' + self._identity_a:<22} {pct(self._n_with_both):>22}  {pct(self._n_a_only):>22}  {pct(self._n_with_a):>18}",
            f"  {'no_'  + self._identity_a:<22} {pct(self._n_b_only):>22}  {pct(self._n_neither):>22}  {pct(self._n_without_a):>18}",
            f"  {'total':<22} {pct(self._n_with_b):>22}  {pct(self._n_without_b):>22}  {pct(n):>18}",
            f"",
            f"  ── Prevalences ────────────────────────────────────────",
            f"  prev_a                : {self._fmt_prop(self.prev_a, self.prev_a_ci)}",
            f"  prev_b                : {self._fmt_prop(self.prev_b, self.prev_b_ci)}",
            f"",
            f"  ── Conditional Probabilities ──────────────────────────",
            f"  P({self._identity_b} | {self._identity_a})".ljust(46) + f": {self._fmt_prop(self.p_b_given_a, self.p_b_given_a_ci)}",
            f"  P({self._identity_b} | no {self._identity_a})".ljust(46) + f": {self._fmt_prop(self.p_b_given_no_a, self.p_b_given_no_a_ci)}",
            f"  P({self._identity_a} | {self._identity_b})".ljust(46) + f": {self._fmt_prop(self.p_a_given_b, self.p_a_given_b_ci)}",
            f"  P({self._identity_a} | no {self._identity_b})".ljust(46) + f": {self._fmt_prop(self.p_a_given_no_b, self.p_a_given_no_b_ci)}",
            f"",
            f"  ── Association Measures ───────────────────────────────",
            f"  prevalence_ratio      : {self._fmt_measure(self.prevalence_ratio, self.prevalence_ratio_ci)}",
            f"",
            f"  ── Interpretation Note ────────────────────────────",
            f"  {self.disclaimer.replace(chr(10), chr(10) + '  ')}",
        ]
        return "\n".join(lines)
