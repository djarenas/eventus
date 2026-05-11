"""
event_semantics.py
EventSemantics — maps generic concepts to specific column names.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
import yaml

_ERROR_PREFIX = "[EventSemantics] Error"

REQUIRED_FIELDS = {"entity_id_col", "start_time_col", "end_time_col"}
OPTIONAL_FIELDS = {"identity", "event_id_col", "event_type_col", "metadata_cols"}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass
class EventSemantics:
    """
    'I am a description of what columns mean in event data. I hold no data and do no computation.'
        
    Maps generic concepts to specific column names in a DataFrame.
 
    The identity attribute names what kind of events these are —
    e.g. 'medicaid_coverage', 'inpatient_hospitalization', 'ed_visits'.
    No spaces allowed — use underscores.
 
    Parameters
    ----------
    entity_id_col : str
        Column identifying the entity (patient, member, etc.).
    start_time_col : str
        Column for event start date.
    end_time_col : str
        Column for event end date.
    identity : str | None
        What kind of events these are. No spaces. Default None.
    event_id_col : str | None
        Optional column for a unique event identifier.
    event_type_col : str | None
        Optional column for event type/category.
    metadata_cols : list[str]
        Optional additional columns to carry through validation.
    """
 
    entity_id_col:  str
    start_time_col: str
    end_time_col:   str
    identity:       str | None = None
    event_id_col:   str | None = None
    event_type_col: str | None = None
    metadata_cols:  list[str]  = field(default_factory=list)
 
    def __post_init__(self) -> None:
        if self.identity is not None:
            if not re.match(r'^[a-zA-Z0-9_]+$', self.identity):
                raise ValueError(
                    f"{_ERROR_PREFIX}: identity {self.identity!r} contains "
                    f"invalid characters. Use only letters, numbers, and "
                    f"underscores e.g. 'medicaid_coverage' not "
                    f"'{self.identity}'"
                )
 
    @classmethod
    def build_from_yaml(cls, path: str) -> "EventSemantics":
        """
        Build an EventSemantics from a YAML file.
 
        Example YAML
        ------------
        entity_id_col:  patient_id
        start_time_col: admit_date
        end_time_col:   discharge_date
        identity:       inpatient_hospitalization
        """
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
        cls._validate_yaml(cfg, path)
        return cls(**cfg)

    @staticmethod
    def _validate_yaml(config: dict, path: str) -> None:
        if not isinstance(config, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML at '{path}' must be a mapping, "
                f"got {type(config).__name__}"
            )
        missing = REQUIRED_FIELDS - config.keys()
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: missing required fields in '{path}': {missing}"
            )
        unknown = config.keys() - ALL_FIELDS
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unrecognized fields in '{path}': {unknown}"
            )
        for field_name in REQUIRED_FIELDS:
            if field_name in config and not isinstance(config[field_name], str):
                raise TypeError(
                    f"{_ERROR_PREFIX}: field '{field_name}' in '{path}' "
                    f"must be a string, got {type(config[field_name]).__name__}"
                )

    def __repr__(self) -> str:
        return (
            f"EventSemantics(\n"
            f"  identity       : {self.identity!r}\n"
            f"  entity_id_col  : '{self.entity_id_col}'\n"
            f"  start_time_col : '{self.start_time_col}'\n"
            f"  end_time_col   : '{self.end_time_col}'\n"
            f")"
        )
