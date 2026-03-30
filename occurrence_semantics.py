"""
occurrence_semantics.py
Semantics for point-in-time occurrence data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import yaml

REQUIRED_FIELDS = {"entity_id_col", "date_col"}
OPTIONAL_FIELDS = {"identity", "occurrence_id_col", "metadata_cols"}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass
class OccurrenceSemantics:
    """
    A description of what columns mean in occurrence data.

    Maps generic concepts (entity, date) to specific column names in a
    DataFrame. Type identity is carried by the OccurrenceSemantics object
    itself via the `identity` attribute — not by a column. Different
    occurrence types should be represented as separate Occurrences objects.

    Attributes
    ----------
    entity_id_col : str
        Column containing entity identifiers.
    date_col : str
        Column containing occurrence dates.
    identity : str | None
        Human-readable label for what this occurrence represents,
        e.g. "Hepatitis B vaccination", "Index diagnosis", "Enrollment".
        Used in reprs, plot titles, and summary labels by downstream analyzers.
    occurrence_id_col : str | None
        Optional column containing unique occurrence identifiers.
    metadata_cols : list[str]
        Optional list of extra data columns to carry through.
    """

    entity_id_col: str
    date_col: str
    identity: str | None = None

    def __post_init__(self) -> None:
        if self.identity is not None and " " in self.identity:
            raise ValueError(
                f"[OccurrenceSemantics] Error: identity must not contain spaces. "
                f"Use underscores instead, e.g. 'hepatitis_b' not '{self.identity}'"
            )
    occurrence_id_col: str | None = None
    metadata_cols: list[str] = field(default_factory=list)

    @classmethod
    def build_from_yaml(cls, path: str) -> "OccurrenceSemantics":
        """
        Build semantics from a YAML configuration file.

        Example YAML
        ------------
        entity_id_col: personid
        date_col: vaccination_date
        identity: Hepatitis B vaccination

        Parameters
        ----------
        path : str
            Path to the YAML file.

        Returns
        -------
        OccurrenceSemantics
            A validated OccurrenceSemantics instance.

        Raises
        ------
        ValueError
            If YAML is missing required fields or has unknown fields.
        TypeError
            If field types are wrong.
        """
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        cls._validate_yaml(config, path)
        return cls(**config)

    @staticmethod
    def _validate_yaml(config: dict, path: str) -> None:
        """
        Validate the structure and types of a YAML config.

        Raises
        ------
        ValueError
            If config is not a dict, missing required fields,
            or has unrecognized fields.
        TypeError
            If field types are wrong.
        """
        if not isinstance(config, dict):
            raise ValueError(
                f"YAML at '{path}' must be a mapping, got {type(config).__name__}"
            )

        missing = REQUIRED_FIELDS - config.keys()
        if missing:
            raise ValueError(
                f"Missing required fields in '{path}': {missing}"
            )

        unknown = config.keys() - ALL_FIELDS
        if unknown:
            raise ValueError(
                f"Unrecognized fields in '{path}': {unknown}"
            )

        for f in REQUIRED_FIELDS:
            if f in config and not isinstance(config[f], str):
                raise TypeError(
                    f"Field '{f}' in '{path}' must be a string, "
                    f"got {type(config[f]).__name__}"
                )

        if config.get("identity") is not None and not isinstance(config["identity"], str):
            raise TypeError(
                f"Field 'identity' in '{path}' must be a string or null"
            )

        if config.get("occurrence_id_col") is not None and not isinstance(config["occurrence_id_col"], str):
            raise TypeError(
                f"Field 'occurrence_id_col' in '{path}' must be a string or null"
            )

        meta = config.get("metadata_cols")
        if meta is not None:
            if not isinstance(meta, list) or not all(isinstance(m, str) for m in meta):
                raise TypeError(
                    f"Field 'metadata_cols' in '{path}' must be a list of strings"
                )

    def __repr__(self) -> str:
        lines = ["OccurrenceSemantics"]
        if self.identity:
            lines.append(f"  identity      : {self.identity}")
        lines.append(f"  entity_id_col : {self.entity_id_col}")
        lines.append(f"  date_col      : {self.date_col}")
        if self.occurrence_id_col:
            lines.append(f"  occurrence_id : {self.occurrence_id_col}")
        if self.metadata_cols:
            lines.append(f"  metadata      : {self.metadata_cols}")
        return "\n".join(lines)
