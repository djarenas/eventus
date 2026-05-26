"""
event_volume.py
EventVolume — per-entity event count result object.
Produced by CohortTimelineEventAnalyzer.compute_volume().
"""
from __future__ import annotations
import pandas as pd

from .event_result import EventResult
from .event_result_utils import format_n_pct

_ERROR = "[EventVolume] Error"
_REQUIRED_COLS = {"n"}


class EventResultVolume(EventResult):
    """
    I hold per-entity event counts for one identity within a CohortTimeline.

    Produced by
    -----------
    CohortTimelineEventAnalyzer.compute_volume()

    Columns in data (beyond base)
    -----------------------------
    n : int
        Number of events within the obs period. 0 is valid.

    Enables
    -------
    - Histogram of N per entity
    - % of cohort with any event
    - % of cohort with multiple events
    """

    def __init__(
        self,
        data:       pd.DataFrame,
        entity_col: str,
        identity:   str,
    ) -> None:
        super().__init__(data, entity_col, identity)

        missing = _REQUIRED_COLS - set(self._data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}."
            )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def n_with_any(self) -> int:
        return int((self._data["n"] > 0).sum())

    @property
    def n_with_multiple(self) -> int:
        return int((self._data["n"] > 1).sum())

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def _repr_fields(self) -> dict:
        return {
            "identity"      : self._identity,
            "entity_col"    : self._entity_col,
            "entities"      : f"{self.n_entities:,}",
            "n_with_any"    : format_n_pct(self.n_with_any,      self.n_entities),
            "n_with_multiple": format_n_pct(self.n_with_multiple, self.n_entities),
        }
