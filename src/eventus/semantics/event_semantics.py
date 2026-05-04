"""
event_semantics.py
EventSemantics — maps generic concepts to specific column names.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import yaml

_ERROR_PREFIX = "[EventSemantics] Error"


@dataclass
class EventSemantics:
    """
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
            import re
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
        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
                f"got {type(cfg).__name__}"
            )
        valid_keys = set(cls.__dataclass_fields__.keys())
        unknown = set(cfg.keys()) - valid_keys
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown keys in YAML: {sorted(unknown)}. "
                f"Valid keys: {sorted(valid_keys)}"
            )
        return cls(**cfg)
 
    def __repr__(self) -> str:
        return (
            f"EventSemantics(\n"
            f"  identity       : {self.identity!r}\n"
            f"  entity_id_col  : '{self.entity_id_col}'\n"
            f"  start_time_col : '{self.start_time_col}'\n"
            f"  end_time_col   : '{self.end_time_col}'\n"
            f")"
        )