"""
cohort_timeline.py
CohortTimeline — per-entity table of episodes, events, and observation
periods. One row per entity. Multi-value columns stored as pipe-delimited
strings.
"""
from __future__ import annotations
import pandas as pd
from typing import Optional

from eventus.data_objects.episodes import Episodes
from eventus.data_objects.events import Events
from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

from . import cohort_timeline_utils as utils

_ERROR = "[CohortTimeline] Error"

class CohortTimeline:
    """
    I am a per-entity table of episodes, events, and observation periods.
    One row per entity. Multi-value columns are stored as pipe-delimited strings.

    Structural invariants
    ---------------------
    - Exactly zero or one observation period layer
    - Zero or more episode layers, each with a unique identity
    - Zero or more event layers, each with a unique identity
    - Zero or more computed event layers (evt_comp_{identity}_{stat})
    - At least one layer must be present
    - One row per entity -- entity_col must be unique and non-null

    Column taxonomy
    ---------------
    {entity_col}                          — entity spine
    obs_start, obs_end, obs_duration_days — observation period
    eps_{identity}_starts/ends            — raw episodes (pipe-delimited)
    evt_{identity}                        — raw events (pipe-delimited)
    evt_comp_{identity}_{stat}            — computed event stats
    """

    _data:                          pd.DataFrame
    _entity_col:                    str
    _has_obs_period:                bool
    _episode_identities:              list[str]
    _event_identities:         list[str]
    _computed_episode_identities:      list[str]
    _computed_event_identities: list[str]
    _episode_descriptor_cols:         dict[str, list[str]]
    _event_descriptor_cols:    dict[str, list[str]]

    def __init__(self, data: pd.DataFrame, entity_col: str) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR} data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if not isinstance(entity_col, str) or not entity_col.strip():
            raise TypeError(
                f"{_ERROR} entity_col must be a non-empty string, "
                f"got {entity_col!r}"
            )

        columns = data.columns.tolist()
        utils.validate_entity_col(data, entity_col)
        utils.validate_obs_period_cols(columns)
        utils.validate_episode_cols(columns)
        utils.validate_event_cols(columns)

        episode_identities        = utils.infer_episode_identities(columns)
        event_identities   = utils.infer_event_identities(columns)
        computed_eps_identities = utils.infer_computed_episode_identities(columns, episode_identities)
        computed_evt_identities = utils.infer_computed_event_identities(columns, event_identities)
        has_obs_period          = utils.OBS_START_COL in columns and utils.OBS_END_COL in columns
        episode_descriptor_cols   = utils.infer_episode_descriptor_cols(columns, episode_identities)
        event_descriptor_cols = utils.infer_event_descriptor_cols(columns, event_identities)

        utils.validate_no_duplicate_identities(episode_identities, event_identities)
        utils.validate_at_least_one_layer(has_obs_period, episode_identities, event_identities)

        self._data                           = data.reset_index(drop=True).copy()
        self._entity_col                     = entity_col
        self._has_obs_period                 = has_obs_period
        self._episode_identities               = episode_identities
        self._event_identities          = event_identities
        self._computed_episode_identities      = computed_eps_identities
        self._computed_event_identities = computed_evt_identities
        self._episode_descriptor_cols          = episode_descriptor_cols
        self._event_descriptor_cols     = event_descriptor_cols

    def copy(self) -> "CohortTimeline":
        return CohortTimeline(self._data.copy(), self._entity_col)

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    @property
    def entity_col(self) -> str:
        return self._entity_col

    @property
    def has_obs_period(self) -> bool:
        return self._has_obs_period

    @property
    def episode_identities(self) -> list[str]:
        return list(self._episode_identities)

    @property
    def event_identities(self) -> list[str]:
        return list(self._event_identities)

    @property
    def computed_event_identities(self) -> list[str]:
        return list(self._computed_event_identities)

    @property
    def computed_episode_identities(self) -> list[str]:
        return list(self._computed_episode_identities)

    @property
    def episode_descriptor_cols(self) -> dict[str, list[str]]:
        """
        Descriptor columns carried from Episodes objects.
        Maps identity → list of column names.
        e.g. {"inpatient_hospitalization": ["hospital_id", "icd10_condition"]}
        Access via ct.data["eps_{identity}_{col}"].
        """
        return dict(self._episode_descriptor_cols)

    @property
    def event_descriptor_cols(self) -> dict[str, list[str]]:
        """
        Descriptor columns carried from Events objects.
        Maps identity → list of column names.
        e.g. {"ed_visit": ["hospital_id", "icd10_condition"]}
        Access via ct.data["evt_{identity}_{col}"].
        """
        return dict(self._event_descriptor_cols)

    def get_event_descriptor(
        self,
        identity: str,
        col:      str,
    ) -> "pd.Series":
        """
        Return the descriptor column for a given event identity
        and column name. Raises if not present.

        Parameters
        ----------
        identity : str
            Event identity e.g. "ed_visit".
        col : str
            Descriptor column name e.g. "icd10_condition".

        Returns
        -------
        pd.Series
            One value per entity — the pipe-delimited or aggregated
            descriptor values for that event identity.
        """
        col_name = f"evt_{identity}_{col}"
        if col_name not in self._data.columns:
            available = self._event_descriptor_cols.get(identity, [])
            raise ValueError(
                f"[CohortTimeline] Error: descriptor column '{col}' not found "
                f"for identity '{identity}'. "
                f"Available: {available}. "
                f"Ensure EventSemantics.descriptor_cols declares '{col}' "
                f"with timeline != 'none'."
            )
        return self._data[col_name].copy()

    def get_episode_descriptor(
        self,
        identity: str,
        col:      str,
    ) -> "pd.Series":
        """
        Return the descriptor column for a given episode identity
        and column name. Raises if not present.

        Parameters
        ----------
        identity : str
            Episode identity e.g. "inpatient_hospitalization".
        col : str
            Descriptor column name e.g. "icd10_condition".

        Returns
        -------
        pd.Series
            One value per entity — the pipe-delimited or aggregated
            descriptor values for that episode identity.
        """
        col_name = f"eps_{identity}_{col}"
        if col_name not in self._data.columns:
            available = self._episode_descriptor_cols.get(identity, [])
            raise ValueError(
                f"[CohortTimeline] Error: descriptor column '{col}' not found "
                f"for identity '{identity}'. "
                f"Available: {available}. "
                f"Ensure EpisodeSemantics.descriptor_cols declares '{col}' "
                f"with timeline != 'none'."
            )
        return self._data[col_name].copy()

    @classmethod
    def build_from_components(
        cls,
        obs_period:  Optional[ObsPeriodPerEntity] = None,
        episodes:      Optional[Episodes | list[Episodes]] = None,
        events: Optional[Events | list[Events]] = None,
    ) -> "CohortTimeline":
        """
        Assemble a CohortTimeline from data objects.
        Dumb assembler -- no analysis performed.
        """
        if obs_period is None and episodes is None and events is None:
            raise ValueError(
                f"{_ERROR} build_from_components() requires at least one of "
                f"obs_period, episodes, or events."
            )

        episodes_list = utils.normalize_to_list(episodes, Episodes, "episodes")
        evt_list    = utils.normalize_to_list(events, Events, "events")

        utils.validate_components(obs_period, episodes_list, evt_list)
        entity_col = utils.resolve_entity_col(obs_period, episodes_list, evt_list)

        result = (
            utils.build_obs_period_df(obs_period, entity_col)
            if obs_period is not None
            else utils.build_entity_spine(episodes_list, evt_list, entity_col)
        )

        for evt in episodes_list:
            result = utils.attach_episode_columns(result, evt, entity_col)
        for occ in evt_list:
            result = utils.attach_event_columns(result, occ, entity_col)

        return cls(result.reset_index(drop=True), entity_col)

    def sample_subset(self, n: int, random_seed: int = 42) -> "CohortTimeline":
        """
        Return a new CohortTimeline with a random subset of n entities.

        Raises
        ------
        ValueError
            If n exceeds the number of entities in the CohortTimeline.
        """
        if n > len(self):
            raise ValueError(
                f"{_ERROR} n={n} exceeds the number of entities ({len(self):,}). "
                f"Cannot sample more entities than are present."
            )
        sampled = self._data.sample(n=n, random_state=random_seed).reset_index(drop=True)
        return CohortTimeline(sampled, self._entity_col)

    def enrich_with_episode_analysis(self, episode_identity: str) -> "CohortTimeline":
        """
        Return a new CohortTimeline enriched with eps_comp_{episode_identity}_*
        coverage columns. Always overwrites existing columns.

        Raises
        ------
        TypeError / ValueError
            Forwarded from CohortTimelineEpisodeAnalyzer, prefixed with
            [CohortTimeline] Error.
        """
        from eventus.analyzers.cohort_timeline_episode_analyzer import CohortTimelineEpisodeAnalyzer
        try:
            analyzer = CohortTimelineEpisodeAnalyzer(self, episode_identity)
            return analyzer.enrich_with_episode_coverage()
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"{_ERROR}: {exc}") from exc

    def enrich_with_event_volume_analysis(self, event_identity: str) -> "CohortTimeline":
        """
        Return a new CohortTimeline enriched with evt_comp_{event_identity}_n.
        Always overwrites existing columns.

        Raises
        ------
        TypeError / ValueError
            Forwarded from CohortTimelineEventAnalyzer, prefixed with
            [CohortTimeline] Error.
        """
        from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
        try:
            analyzer = CohortTimelineEventAnalyzer(self, event_identity)
            return analyzer.enrich_with_volume()
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"{_ERROR}: {exc}") from exc

    def enrich_with_event_timing_analysis(self, event_identity: str, max_n: int) -> "CohortTimeline":
        """
        Return a new CohortTimeline enriched with
        evt_comp_{event_identity}_time_to_1 ... time_to_{max_n} and recency_days.
        Always overwrites existing columns.

        Parameters
        ----------
        max_n : int
            Maximum nth event to compute timing for. Must be >= 1.

        Raises
        ------
        TypeError / ValueError
            Forwarded from CohortTimelineEventAnalyzer, prefixed with
            [CohortTimeline] Error.
        """
        from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
        try:
            analyzer = CohortTimelineEventAnalyzer(self, event_identity)
            return analyzer.enrich_with_timing(max_n)
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"{_ERROR}: {exc}") from exc

    def enrich_with_event_shape_analysis(self, event_identity: str) -> "CohortTimeline":
        """
        Return a new CohortTimeline enriched with evt_comp_{event_identity}_mean_gap,
        std_gap, cv_gap, min_gap, max_gap, burstiness, memory, density, center_of_mass.
        Always overwrites existing columns.

        Raises
        ------
        TypeError / ValueError
            Forwarded from CohortTimelineEventAnalyzer, prefixed with
            [CohortTimeline] Error.
        """
        from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
        try:
            analyzer = CohortTimelineEventAnalyzer(self, event_identity)
            return analyzer.enrich_with_shape()
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"{_ERROR}: {exc}") from exc

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        eps_desc = {k: v for k, v in self._episode_descriptor_cols.items() if v}
        evt_desc = {k: v for k, v in self._event_descriptor_cols.items() if v}
        return (
            f"CohortTimeline(\n"
            f"  entities                      : {len(self):,}\n"
            f"  entity_col                    : '{self._entity_col}'\n"
            f"  has_obs_period                : {self._has_obs_period}\n"
            f"  episode_identities              : {self._episode_identities}\n"
            f"  episode_descriptor_cols         : {eps_desc}\n"
            f"  computed_episode_identities     : {self._computed_episode_identities}\n"
            f"  event_identities         : {self._event_identities}\n"
            f"  event_descriptor_cols    : {evt_desc}\n"
            f"  computed_event_identities: {self._computed_event_identities}\n"
            f")"
        )
