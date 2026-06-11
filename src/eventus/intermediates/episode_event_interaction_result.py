"""
episode_event_interaction_result.py
EpisodeEventInteractionResult — per-entity event counts by episode segment.

Produced by EpisodeEventInteractionAnalyzer.compute_interaction().

Columns (one row per entity):
    entity_col          — entity identifier
    obs_start           — observation period start
    obs_end             — observation period end
    n_before            — events before the first episode
    n_during            — events during active episodes
    n_gaps              — events during gaps between episodes
    n_after             — events after the last episode
    n_no_episodes       — events for members with no episodes (NaN if member has episodes)

NaN semantics:
    n_before / n_during / n_gaps / n_after are NaN for members with no episodes.
    n_no_episodes is NaN for members with at least one episode.
    A member with episodes but no gaps has n_gaps = 0 (not NaN) — zero is a real count.
"""
from __future__ import annotations
import pandas as pd


class EpisodeEventInteractionResult:
    """
    I hold per-entity event counts classified by their position
    relative to a member's episode structure.

    Attributes
    ----------
    data             : pd.DataFrame   one row per entity
    entity_col       : str
    episode_identity : str
    event_identity   : str
    """

    # ── Attributes ────────────────────────────────────────────────────
    _data:             pd.DataFrame
    _entity_col:       str
    _episode_identity: str
    _event_identity:   str

    def __init__(
        self,
        data:             pd.DataFrame,
        entity_col:       str,
        episode_identity: str,
        event_identity:   str,
    ) -> None:
        self._data             = data
        self._entity_col       = entity_col
        self._episode_identity = episode_identity
        self._event_identity   = event_identity

    # ── Properties ────────────────────────────────────────────────────

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def entity_col(self) -> str:
        return self._entity_col

    @property
    def episode_identity(self) -> str:
        return self._episode_identity

    @property
    def event_identity(self) -> str:
        return self._event_identity

    @property
    def n_entities(self) -> int:
        return len(self._data)

    @property
    def n_with_episodes(self) -> int:
        return int(self._data["n_no_episodes"].isna().sum())

    @property
    def n_without_episodes(self) -> int:
        return int(self._data["n_no_episodes"].notna().sum())

    # ── Dunder ────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return self.n_entities

    def __repr__(self) -> str:
        n_gaps      = int((self._data["n_gaps"] > 0).sum())
        n_before    = int((self._data["n_before"] > 0).sum())
        n_after     = int((self._data["n_after"] > 0).sum())
        n_no_eps    = self.n_without_episodes
        total       = self.n_entities

        def pct(n): return f"({round(100 * n / total, 1)}%)" if total > 0 else ""

        n_during    = int((self._data["n_during"] > 0).sum())

        return (
            f"EpisodeEventInteractionResult:\n"
            f"  episode_identity : {self._episode_identity}\n"
            f"  event_identity   : {self._event_identity}\n"
            f"  entity_col       : {self._entity_col}\n"
            f"  entities         : {total:,}\n"
            f"  with episodes    : {self.n_with_episodes:,} {pct(self.n_with_episodes)}\n"
            f"  without episodes : {n_no_eps:,} {pct(n_no_eps)}\n"
            f"  events before first episode  : {n_before:,} entities {pct(n_before)}\n"
            f"  events during active episodes: {n_during:,} entities {pct(n_during)}\n"
            f"  events during gaps           : {n_gaps:,} entities {pct(n_gaps)}\n"
            f"  events after last episode    : {n_after:,} entities {pct(n_after)}\n"
        )
