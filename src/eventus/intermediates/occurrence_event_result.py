"""
occurrence_event_result.py
OccurrenceEventResult — per-entity temporal relationship statistics
between one occurrence identity and one event identity.

Produced by OccurrenceEventAnalyzer.compute().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_ERROR = "[OccurrenceEventResult] Error"

_REQUIRED_COLS = {
    "obs_start", "obs_end",
    "n_occ_total", "n_events_total",
    "n_occ_within", "pct_occ_within",
    "mean_days_occ_to_event", "median_days_occ_to_event", "std_days_occ_to_event",
    "mean_days_event_to_occ", "median_days_event_to_occ", "std_days_event_to_occ",
}


class OccurrenceEventResult:
    """
    Per-entity temporal relationship statistics between one occurrence
    identity and one event identity within a CohortTimeline.

    Produced by
    -----------
    OccurrenceEventAnalyzer.compute()

    Columns in data (beyond entity_col)
    ------------------------------------
    obs_start, obs_end

    Volume:
        n_occ_total          : int   — total occurrences in obs period
        n_events_total       : int   — total events in obs period

    Within:
        n_occ_within         : int   — occurrences that fell inside any event
        pct_occ_within       : float — n_occ_within / n_occ_total
                                       NaN if n_occ_total = 0

    Gap stats — nearest event start after each occurrence:
        mean_days_occ_to_event    : float  — NaN if no qualifying pairs
        median_days_occ_to_event  : float  — NaN if no qualifying pairs
        std_days_occ_to_event     : float  — NaN if < 2 pairs

    Gap stats — nearest occurrence after each event discharge:
        mean_days_event_to_occ    : float  — NaN if no qualifying pairs
        median_days_event_to_occ  : float  — NaN if no qualifying pairs
        std_days_event_to_occ     : float  — NaN if < 2 pairs

    NaN semantics
    -------------
    NaN in gap stats may mean:
        - Entity had no occurrences (n_occ_total = 0)
        - Entity had no events (n_events_total = 0)
        - Entity had both but no qualifying temporal pairs in obs period
        - Entity had only one qualifying pair (std only)
    All are scientifically valid — absent signal, not missing data.
    """

    _data:             pd.DataFrame
    _entity_col:       str
    _identity_occ:     str
    _identity_event:   str

    def __init__(
        self,
        data:           pd.DataFrame,
        entity_col:     str,
        identity_occ:   str,
        identity_event: str,
    ) -> None:
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError(f"{_ERROR}: data must be a non-empty DataFrame.")
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' not found in data."
            )
        if data[entity_col].isnull().any():
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' has null values."
            )
        if data[entity_col].duplicated().any():
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' is not unique. "
                f"OccurrenceEventResult requires one row per entity."
            )
        missing = _REQUIRED_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR}: data is missing required columns: {sorted(missing)}."
            )

        self._data           = data.reset_index(drop=True).copy()
        self._entity_col     = entity_col
        self._identity_occ   = identity_occ
        self._identity_event = identity_event

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    @property
    def entity_col(self) -> str:
        return self._entity_col

    @property
    def identity_occ(self) -> str:
        return self._identity_occ

    @property
    def identity_event(self) -> str:
        return self._identity_event

    @property
    def n_entities(self) -> int:
        return len(self._data)

    @property
    def n_with_both(self) -> int:
        """Entities with at least one occurrence AND at least one event."""
        return int(
            ((self._data["n_occ_total"] > 0) &
             (self._data["n_events_total"] > 0)).sum()
        )

    @property
    def n_occ_only(self) -> int:
        """Entities with occurrences but no events."""
        return int(
            ((self._data["n_occ_total"] > 0) &
             (self._data["n_events_total"] == 0)).sum()
        )

    @property
    def n_event_only(self) -> int:
        """Entities with events but no occurrences."""
        return int(
            ((self._data["n_occ_total"] == 0) &
             (self._data["n_events_total"] > 0)).sum()
        )

    @property
    def n_neither(self) -> int:
        """Entities with neither occurrences nor events."""
        return int(
            ((self._data["n_occ_total"] == 0) &
             (self._data["n_events_total"] == 0)).sum()
        )

    @property
    def n_with_occ_to_event_gap(self) -> int:
        """Entities with at least one qualifying occ → event pair."""
        return int(self._data["mean_days_occ_to_event"].notna().sum())

    @property
    def n_with_event_to_occ_gap(self) -> int:
        """Entities with at least one qualifying event → occ pair."""
        return int(self._data["mean_days_event_to_occ"].notna().sum())

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100*x/n, 1)}%)" if n else str(x)

        n_occ_total = int(self._data["n_occ_total"].sum())
        n_within    = int(self._data["n_occ_within"].sum())

        med_occ_to_evt = round(
            float(self._data["median_days_occ_to_event"].dropna().median()), 1
        ) if self._data["median_days_occ_to_event"].notna().any() else "NaN"

        med_evt_to_occ = round(
            float(self._data["median_days_event_to_occ"].dropna().median()), 1
        ) if self._data["median_days_event_to_occ"].notna().any() else "NaN"

        return (
            f"OccurrenceEventResult:\n"
            f"  identity_occ           : {self._identity_occ}\n"
            f"  identity_event         : {self._identity_event}\n"
            f"  entity_col             : {self._entity_col}\n"
            f"  entities               : {n:,}\n"
            f"  {'─'*44}\n"
            f"  n_with_both            : {pct(self.n_with_both)}\n"
            f"  n_occ_only             : {pct(self.n_occ_only)}\n"
            f"  n_event_only           : {pct(self.n_event_only)}\n"
            f"  n_neither              : {pct(self.n_neither)}\n"
            f"  {'─'*44}\n"
            f"  n_occ_total            : {n_occ_total:,} (across all entities)\n"
            f"  n_occ_within           : {n_within:,}\n"
            f"  {'─'*44}\n"
            f"  n_with_occ_to_event    : {pct(self.n_with_occ_to_event_gap)}\n"
            f"  median_occ_to_event    : {med_occ_to_evt} days\n"
            f"  n_with_event_to_occ    : {pct(self.n_with_event_to_occ_gap)}\n"
            f"  median_event_to_occ    : {med_evt_to_occ} days\n"
        )
