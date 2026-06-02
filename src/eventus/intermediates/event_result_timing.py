"""
event_result_timing.py
EventResultTiming — per-entity nth-event timing result object.
Produced by CohortTimelineEventAnalyzer.compute_timing().
"""
from __future__ import annotations
import pandas as pd

from .event_result import EventResult
from .event_result_utils import format_n_pct

_ERROR = "[EventTiming] Error"


class EventResultTiming(EventResult):
    """
    I hold per-entity timing stats for one identity within a CohortTimeline.

    Produced by
    -----------
    CohortTimelineEventAnalyzer.compute_timing(max_n)

    Columns in data (beyond base)
    -----------------------------
    time_to_1, ..., time_to_{max_n} : float
        Days from obs_start to the nth event.
        NaN where entity has fewer than n events.
    recency_days : float
        Days from last event to obs_end.
        NaN for entities with zero events.

    Enables
    -------
    - Histogram of time_to_1, time_to_2, ... (overlaid or faceted)
    - KM-style plot of time-to-first across the cohort
    - Each nth histogram plotted over the eligible sub-cohort (n >= nth),
      denominator available via EventVolume
    """

    # ── Attributes ───────────────────────────────────────────────────────
    # Inherited from EventResult
    _data:       pd.DataFrame  # validated per-entity DataFrame
    _entity_col: str           # entity identifier column name
    _identity:   str           # event identity label
    # Own
    _max_n: int                # maximum nth event timing computed

    def __init__(
        self,
        data:       pd.DataFrame,
        entity_col: str,
        identity:   str,
        max_n:      int,
    ) -> None:
        super().__init__(data, entity_col, identity)

        if not isinstance(max_n, int) or max_n < 1:
            raise ValueError(
                f"{_ERROR} max_n must be an integer >= 1, got {max_n!r}"
            )

        # Validate all expected timing columns are present
        expected = {f"time_to_{nth}" for nth in range(1, max_n + 1)} | {"recency_days"}
        missing  = expected - set(self._data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}."
            )

        self._max_n = max_n

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def max_n(self) -> int:
        return self._max_n

    def n_with_timing(self, nth: int) -> int:
        """
        Number of entities that have a valid (non-NaN) time_to_{nth}.

        Parameters
        ----------
        nth : int
            Which nth event to count. Must be between 1 and max_n.

        Raises
        ------
        ValueError if nth is outside [1, max_n].
        """
        if not 1 <= nth <= self._max_n:
            raise ValueError(
                f"{_ERROR} nth must be between 1 and max_n ({self._max_n}), "
                f"got {nth}"
            )
        return int(self._data[f"time_to_{nth}"].notna().sum())

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def _repr_fields(self) -> dict:
        fields = {
            "identity"  : self._identity,
            "entity_col": self._entity_col,
            "entities"  : f"{self.n_entities:,}",
            "max_n"     : self._max_n,
        }
        for nth in range(1, self._max_n + 1):
            n = self.n_with_timing(nth)
            fields[f"n_with_{nth}th"] = format_n_pct(n, self.n_entities)
        return fields
