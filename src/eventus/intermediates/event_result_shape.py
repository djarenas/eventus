"""
event_result_shape.py
EventResultShape — per-entity behavioral fingerprint result object.
Produced by CohortTimelineEventAnalyzer.compute_shape().
"""
from __future__ import annotations
import pandas as pd

from .event_result import EventResult
from .event_result_utils import format_n_pct

_ERROR = "[EventResultShape] Error"

_REQUIRED_COLS = {
    "mean_gap", "std_gap", "cv_gap", "min_gap", "max_gap",
    "burstiness", "memory", "density", "center_of_mass",
}


class EventResultShape(EventResult):
    """
    I hold per-entity behavioral fingerprint stats for one identity
    within a CohortTimeline.

    Produced by
    -----------
    CohortTimelineEventAnalyzer.compute_shape()

    Columns in data (beyond base)
    -----------------------------
    mean_gap       : float  — requires n >= 2
    std_gap        : float  — requires n >= 3
    cv_gap         : float  — requires n >= 3
    min_gap        : float  — requires n >= 2
    max_gap        : float  — requires n >= 2
    burstiness     : float  — requires n >= 3
    memory         : float  — requires n >= 4
    density        : float  — requires n >= 1, obs_duration > 0
    center_of_mass : float  — requires n >= 1, obs_duration > 0

    All stats are NaN where the minimum event threshold is not met.
    This is by design — the entity simply did not have enough data.

    Enables
    -------
    - Scatter plot of burstiness vs memory (behavioral fingerprint)
    - Histogram of center_of_mass (front-loaded vs back-loaded cohort)
    - Density distribution across the cohort
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
    def n_with_gaps(self) -> int:
        """Number of entities with at least 2 events (gap stats defined)."""
        return int(self._data["mean_gap"].notna().sum())

    @property
    def n_with_shape(self) -> int:
        """Number of entities with at least 3 events (burstiness defined)."""
        return int(self._data["burstiness"].notna().sum())

    @property
    def n_with_memory(self) -> int:
        """Number of entities with at least 4 events (memory defined)."""
        return int(self._data["memory"].notna().sum())

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def _repr_fields(self) -> dict:
        return {
            "identity"      : self._identity,
            "entity_col"    : self._entity_col,
            "entities"      : f"{self.n_entities:,}",
            "n_with_gaps"   : format_n_pct(self.n_with_gaps,   self.n_entities),
            "n_with_shape"  : format_n_pct(self.n_with_shape,  self.n_entities),
            "n_with_memory" : format_n_pct(self.n_with_memory, self.n_entities),
        }
