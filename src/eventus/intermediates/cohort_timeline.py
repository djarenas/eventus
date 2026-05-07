"""cohort_timeline.py  
CohortTimeline — per-entity table of events, occurrences, and observation  
periods. One row per entity. Multi-value columns stored as pipe-delimited  
strings.  
"""  
from __future__ import annotations  
import pandas as pd  
from typing import Optional  
  
from eventus.data_objects.events import Events  
from eventus.data_objects.occurrences import Occurrences  
from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity
  
from . import cohort_timeline_utils as utils  
  
_ERROR = "[CohortTimeline] Error"  
    
class CohortTimeline:  
    """  
    I am a per-entity table of events, occurrences, and observation periods.  
    One row per entity. Multi-value columns are stored as pipe-delimited strings.  
  
    Structural invariants  
    ---------------------  
    - Exactly zero or one observation period layer  
    - Zero or more event layers, each with a unique identity  
    - Zero or more occurrence layers, each with a unique identity  
    - At least one layer must be present  
    - One row per entity -- entity_col must be unique and non-null  
    """  
  
    # C++-style attribute declarations  
    _data: pd.DataFrame                # validated DataFrame, one row per entity  
    _entity_col: str                   # entity identifier column name  
    _has_obs_period: bool              # whether observation period layer exists  
    _event_identities: list[str]       # list of event identity strings present  
    _occurrence_identities: list[str]  # list of occurrence identity strings present  
  
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
        utils.validate_event_cols(columns)  
  
        event_identities = utils.infer_event_identities(columns)  
        occurrence_identities = utils.infer_occurrence_identities(columns)  
        has_obs_period = utils.OBS_START_COL in columns and utils.OBS_END_COL in columns  
  
        utils.validate_no_duplicate_identities(event_identities, occurrence_identities)  
        utils.validate_at_least_one_layer(has_obs_period, event_identities, occurrence_identities)  
  
        self._data = data.reset_index(drop=True).copy()  
        self._entity_col = entity_col  
        self._has_obs_period = has_obs_period  
        self._event_identities = event_identities  
        self._occurrence_identities = occurrence_identities  
  
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
    def event_identities(self) -> list[str]:  
        return list(self._event_identities)  
  
    @property  
    def occurrence_identities(self) -> list[str]:  
        return list(self._occurrence_identities)  
  
    @classmethod  
    def build_from_components(  
        cls,  
        obs_period: Optional[ObsPeriodPerEntity] = None,  
        events: Optional[Events | list[Events]] = None,  
        occurrences: Optional[Occurrences | list[Occurrences]] = None,  
    ) -> "CohortTimeline":  
        """  
        Assemble a CohortTimeline from data objects.  
        Dumb assembler -- no analysis performed.  
        """  
        if obs_period is None and events is None and occurrences is None:  
            raise ValueError(  
                f"{_ERROR} build_from_components() requires at least one of "  
                f"obs_period, events, or occurrences."  
            )  
  
        events_list = utils.normalize_to_list(events, Events, "events")  
        occ_list = utils.normalize_to_list(occurrences, Occurrences, "occurrences")  
  
        utils.validate_components(obs_period, events_list, occ_list)  
        entity_col = utils.resolve_entity_col(obs_period, events_list, occ_list)  
  
        result = (  
            utils.build_obs_period_df(obs_period, entity_col)  
            if obs_period is not None  
            else utils.build_entity_spine(events_list, occ_list, entity_col)  
        )  
  
        for evt in events_list:  
            result = utils.attach_event_columns(result, evt, entity_col)  
        for occ in occ_list:  
            result = utils.attach_occurrence_columns(result, occ, entity_col)  
  
        return cls(result.reset_index(drop=True), entity_col)  
  
    def __len__(self) -> int:  
        return len(self._data)  
  
    def __repr__(self) -> str:  
        return (  
            f"CohortTimeline(\n"  
            f"  entities             : {len(self):,}\n"  
            f"  entity_col           : '{self._entity_col}'\n"  
            f"  has_obs_period       : {self._has_obs_period}\n"  
            f"  event_identities     : {self._event_identities}\n"  
            f"  occurrence_identities: {self._occurrence_identities}\n"  
            f")"  
        )  