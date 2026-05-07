"""
survival_result.py
SurvivalResult — validated Kaplan-Meier survival curve result object.

Standalone and reusable — not tied to occurrence analysis specifically.
Any analysis that produces a KM-style survival curve produces a
SurvivalResult. Current producers:
- CohortTimelineOccurrenceAnalyzer.compute_survival()

Future producers (examples):
- Time-to-event analyzers
- Treatment comparison analyzers
"""
from __future__ import annotations
import pandas as pd
import numpy as np

_ERROR = "[SurvivalResult] Error"

_REQUIRED_COLS = {
    "day", "n_at_risk", "n_events", "n_censored",
    "survival", "ci_lower", "ci_upper",
}

_VALID_CI_METHODS = {"greenwood"}


class SurvivalResult:
    """
    I am a validated Kaplan-Meier survival curve.

    I am standalone and reusable — I carry everything needed to plot
    and interpret a survival curve without any reference back to the
    object that produced me.

    Structural invariants
    ---------------------
    - data is a non-empty DataFrame with all required columns
    - survival values are in [0, 1]
    - ci_lower <= survival <= ci_upper everywhere
    - n_at_risk is monotonically non-increasing
    - label is a non-empty string
    - n_total, n_events_total, n_censored_total are positive integers
    - n_events_total + n_censored_total == n_total

    Attributes
    ----------
    data : pd.DataFrame
        One row per unique event timepoint. Columns:
        day (int), n_at_risk (int), n_events (int), n_censored (int),
        survival (float), ci_lower (float), ci_upper (float).
    label : str
        Human-readable label for the curve, e.g. 'vaccination'.
        Used in plot titles and legends.
    n_total : int
        Total cohort size including never-occurred entities.
    n_events_total : int
        Total entities who experienced the event.
    n_censored_total : int
        Total entities censored (never experienced the event).
    ci_method : str
        Confidence interval method used. Currently 'greenwood'.
    """

    _data:            pd.DataFrame
    _label:           str
    _n_total:         int
    _n_events_total:  int
    _n_censored_total: int
    _ci_method:       str

    def __init__(
        self,
        data:             pd.DataFrame,
        label:            str,
        n_total:          int,
        n_events_total:   int,
        n_censored_total: int,
        ci_method:        str = "greenwood",
    ) -> None:
        # ── Type checks ───────────────────────────────────────────────
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR} data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if not isinstance(label, str) or not label.strip():
            raise TypeError(
                f"{_ERROR} label must be a non-empty string, "
                f"got {label!r}"
            )
        for name, val in [
            ("n_total",          n_total),
            ("n_events_total",   n_events_total),
            ("n_censored_total", n_censored_total),
        ]:
            if not isinstance(val, int) or val < 0:
                raise TypeError(
                    f"{_ERROR} {name} must be a non-negative integer, "
                    f"got {val!r}"
                )
        if ci_method not in _VALID_CI_METHODS:
            raise ValueError(
                f"{_ERROR} ci_method must be one of "
                f"{sorted(_VALID_CI_METHODS)}, got {ci_method!r}"
            )

        # ── Required columns ──────────────────────────────────────────
        missing = _REQUIRED_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}."
            )

        # ── Allow empty data only when n_events_total == 0 ───────────
        # (cohort with no events produces a valid but empty curve)
        if data.empty and n_events_total > 0:
            raise ValueError(
                f"{_ERROR} data is empty but n_events_total={n_events_total}. "
                f"Empty data is only valid when no events occurred."
            )

        # ── Cohort count consistency ──────────────────────────────────
        if n_total < 1:
            raise ValueError(
                f"{_ERROR} n_total must be >= 1, got {n_total}"
            )
        if n_events_total + n_censored_total != n_total:
            raise ValueError(
                f"{_ERROR} n_events_total ({n_events_total}) + "
                f"n_censored_total ({n_censored_total}) must equal "
                f"n_total ({n_total})."
            )

        if not data.empty:
            # ── Survival bounds ───────────────────────────────────────
            if not data["survival"].between(0.0, 1.0).all():
                bad = data.loc[~data["survival"].between(0.0, 1.0), "survival"].tolist()
                raise ValueError(
                    f"{_ERROR} survival values must be in [0, 1]. "
                    f"Found out-of-range values: {bad[:5]}"
                )

            # ── CI ordering ───────────────────────────────────────────
            if not (data["ci_lower"] <= data["survival"]).all():
                raise ValueError(
                    f"{_ERROR} ci_lower must be <= survival at every timepoint."
                )
            if not (data["survival"] <= data["ci_upper"]).all():
                raise ValueError(
                    f"{_ERROR} ci_upper must be >= survival at every timepoint."
                )

            # ── Monotonic n_at_risk ───────────────────────────────────
            if not (data["n_at_risk"].diff().dropna() <= 0).all():
                raise ValueError(
                    f"{_ERROR} n_at_risk must be monotonically non-increasing."
                )

        self._data             = data.reset_index(drop=True).copy()
        self._label            = label.strip()
        self._n_total          = n_total
        self._n_events_total   = n_events_total
        self._n_censored_total = n_censored_total
        self._ci_method        = ci_method

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    @property
    def label(self) -> str:
        return self._label

    @property
    def n_total(self) -> int:
        return self._n_total

    @property
    def n_events_total(self) -> int:
        return self._n_events_total

    @property
    def n_censored_total(self) -> int:
        return self._n_censored_total

    @property
    def ci_method(self) -> str:
        return self._ci_method

    @property
    def event_rate_pct(self) -> float:
        """Percentage of cohort that experienced the event."""
        return round(100 * self._n_events_total / self._n_total, 1)

    @property
    def median_survival(self) -> float | None:
        """
        Smallest day where S(t) <= 0.5.
        None if the curve never crosses 0.5 (fewer than half the
        cohort experienced the event).
        """
        if self._data.empty:
            return None
        crossed = self._data[self._data["survival"] <= 0.5]
        if crossed.empty:
            return None
        return float(crossed.iloc[0]["day"])

    @property
    def max_day(self) -> int | None:
        """Last timepoint in the survival table."""
        if self._data.empty:
            return None
        return int(self._data["day"].max())

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        """Number of timepoints in the survival table."""
        return len(self._data)

    def __repr__(self) -> str:
        median = (
            f"{self.median_survival:.0f} days"
            if self.median_survival is not None
            else "not reached"
        )
        return (
            f"SurvivalResult:\n"
            f"  label            : {self._label}\n"
            f"  n_total          : {self._n_total:,}\n"
            f"  n_events         : {self._n_events_total:,} "
            f"({self.event_rate_pct}%)\n"
            f"  n_censored       : {self._n_censored_total:,}\n"
            f"  median_survival  : {median}\n"
            f"  timepoints       : {len(self._data):,}\n"
            f"  max_day          : "
            f"{self.max_day if self.max_day is not None else 'n/a'}\n"
            f"  ci_method        : {self._ci_method}\n"
        )
