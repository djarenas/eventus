"""
event_episode_result.py
EventEpisodeResult — per-entity temporal relationship statistics
between one event identity and one episode identity.

Produced by EventEpisodeAnalyzer.compute().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_ERROR = "[EventEpisodeResult] Error"

_REQUIRED_COLS = {
    "obs_start", "obs_end",
    "n_evt_total", "n_episodes_total",
    "n_evt_within", "pct_evt_within",
    "mean_days_evt_to_episode", "median_days_evt_to_episode", "std_days_evt_to_episode",
    "mean_days_episode_to_occ", "median_days_episode_to_occ", "std_days_episode_to_occ",
}


class EventEpisodeResult:
    """
    Per-entity temporal relationship statistics between one event
    identity and one episode identity within a CohortTimeline.

    Produced by
    -----------
    EventEpisodeAnalyzer.compute()

    Columns in data (beyond entity_col)
    ------------------------------------
    obs_start, obs_end

    Volume:
        n_evt_total          : int   — total events in obs period
        n_episodes_total       : int   — total episodes in obs period

    Within:
        n_evt_within         : int   — events that fell inside any episode
        pct_evt_within       : float — n_evt_within / n_evt_total
                                       NaN if n_evt_total = 0

    Gap stats — nearest episode start after each event:
        mean_days_evt_to_episode    : float  — NaN if no qualifying pairs
        median_days_evt_to_episode  : float  — NaN if no qualifying pairs
        std_days_evt_to_episode     : float  — NaN if < 2 pairs

    Gap stats — nearest event after each episode discharge:
        mean_days_episode_to_occ    : float  — NaN if no qualifying pairs
        median_days_episode_to_occ  : float  — NaN if no qualifying pairs
        std_days_episode_to_occ     : float  — NaN if < 2 pairs

    NaN semantics
    -------------
    NaN in gap stats may mean:
        - Entity had no events (n_evt_total = 0)
        - Entity had no episodes (n_episodes_total = 0)
        - Entity had both but no qualifying temporal pairs in obs period
        - Entity had only one qualifying pair (std only)
    All are scientifically valid — absent signal, not missing data.
    """

    _data:             pd.DataFrame
    _entity_col:       str
    _identity_occ:     str
    _identity_episode:   str

    def __init__(
        self,
        data:           pd.DataFrame,
        entity_col:     str,
        identity_occ:   str,
        identity_episode: str,
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
                f"EventEpisodeResult requires one row per entity."
            )
        missing = _REQUIRED_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR}: data is missing required columns: {sorted(missing)}."
            )

        self._data           = data.reset_index(drop=True).copy()
        self._entity_col     = entity_col
        self._identity_occ   = identity_occ
        self._identity_episode = identity_episode

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
    def identity_episode(self) -> str:
        return self._identity_episode

    @property
    def n_entities(self) -> int:
        return len(self._data)

    @property
    def n_with_both(self) -> int:
        """Entities with at least one event AND at least one episode."""
        return int(
            ((self._data["n_evt_total"] > 0) &
             (self._data["n_episodes_total"] > 0)).sum()
        )

    @property
    def n_evt_only(self) -> int:
        """Entities with events but no episodes."""
        return int(
            ((self._data["n_evt_total"] > 0) &
             (self._data["n_episodes_total"] == 0)).sum()
        )

    @property
    def n_episode_only(self) -> int:
        """Entities with episodes but no events."""
        return int(
            ((self._data["n_evt_total"] == 0) &
             (self._data["n_episodes_total"] > 0)).sum()
        )

    @property
    def n_neither(self) -> int:
        """Entities with neither events nor episodes."""
        return int(
            ((self._data["n_evt_total"] == 0) &
             (self._data["n_episodes_total"] == 0)).sum()
        )

    @property
    def n_with_evt_to_episode_gap(self) -> int:
        """Entities with at least one qualifying occ → episode pair."""
        return int(self._data["mean_days_evt_to_episode"].notna().sum())

    @property
    def n_with_episode_to_evt_gap(self) -> int:
        """Entities with at least one qualifying episode → occ pair."""
        return int(self._data["mean_days_episode_to_occ"].notna().sum())

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        n = self.n_entities

        def pct(x):
            return f"{x:,} ({round(100*x/n, 1)}%)" if n else str(x)

        n_evt_total = int(self._data["n_evt_total"].sum())
        n_within    = int(self._data["n_evt_within"].sum())

        med_evt_to_evt = round(
            float(self._data["median_days_evt_to_episode"].dropna().median()), 1
        ) if self._data["median_days_evt_to_episode"].notna().any() else "NaN"

        med_eps_to_occ = round(
            float(self._data["median_days_episode_to_occ"].dropna().median()), 1
        ) if self._data["median_days_episode_to_occ"].notna().any() else "NaN"

        return (
            f"EventEpisodeResult:\n"
            f"  identity_occ           : {self._identity_occ}\n"
            f"  identity_episode         : {self._identity_episode}\n"
            f"  entity_col             : {self._entity_col}\n"
            f"  entities               : {n:,}\n"
            f"  {'─'*44}\n"
            f"  n_with_both            : {pct(self.n_with_both)}\n"
            f"  n_evt_only             : {pct(self.n_evt_only)}\n"
            f"  n_episode_only           : {pct(self.n_episode_only)}\n"
            f"  n_neither              : {pct(self.n_neither)}\n"
            f"  {'─'*44}\n"
            f"  n_evt_total            : {n_evt_total:,} (across all entities)\n"
            f"  n_evt_within           : {n_within:,}\n"
            f"  {'─'*44}\n"
            f"  n_with_evt_to_episode    : {pct(self.n_with_evt_to_episode_gap)}\n"
            f"  median_evt_to_episode    : {med_evt_to_evt} days\n"
            f"  n_with_episode_to_occ    : {pct(self.n_with_episode_to_evt_gap)}\n"
            f"  median_episode_to_occ    : {med_eps_to_occ} days\n"
        )
