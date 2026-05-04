"""
occurrence_semantics.py
Semantics for point-in-time occurrence data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
import yaml

_ERROR_PREFIX = "[OccurrenceSemantics] Error"

REQUIRED_FIELDS = {"entity_id_col", "date_col"}
OPTIONAL_FIELDS = {"identity", "occurrence_id_col", "metadata_cols"}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass
class OccurrenceSemantics:
    """
    A description of what columns mean in occurrence data.

    Maps generic concepts (entity, date) to specific column names in a
    DataFrame. The identity attribute names what kind of occurrences
    these are — e.g. 'hepatitis_b', 'ed_visit', 'index_diagnosis'.
    Only letters, numbers, and underscores allowed in identity.

    Attributes
    ----------
    entity_id_col : str
        Column containing entity identifiers.
    date_col : str
        Column containing occurrence dates.
    identity : str | None
        Label for what this occurrence represents.
        Only letters, numbers, and underscores allowed.
        e.g. 'hepatitis_b' not 'Hepatitis B'
    occurrence_id_col : str | None
        Optional column containing unique occurrence identifiers.
    metadata_cols : list[str]
        Optional list of extra data columns to carry through.
    """

    entity_id_col:    str
    date_col:         str
    identity:         str | None = None
    occurrence_id_col: str | None = None
    metadata_cols:    list[str]  = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.identity is not None:
            if not re.match(r'^[a-zA-Z0-9_]+$', self.identity):
                raise ValueError(
                    f"{_ERROR_PREFIX}: identity {self.identity!r} contains "
                    f"invalid characters. Use only letters, numbers, and "
                    f"underscores e.g. 'hepatitis_b' not '{self.identity}'"
                )

    @classmethod
    def build_from_yaml(cls, path: str) -> "OccurrenceSemantics":
        """
        Build semantics from a YAML configuration file.

        Example YAML
        ------------
        entity_id_col: patient_id
        date_col:      vaccination_date
        identity:      hepatitis_b
        """
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        cls._validate_yaml(config, path)
        return cls(**config)

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
            f"OccurrenceSemantics(\n"
            f"  identity      : {self.identity!r}\n"
            f"  entity_id_col : '{self.entity_id_col}'\n"
            f"  date_col      : '{self.date_col}'\n"
            f")"
        )
