from dataclasses import dataclass, field
import yaml

REQUIRED_FIELDS = {"entity_id_col", "start_time_col", "end_time_col"}
OPTIONAL_FIELDS = {"event_type_col", "event_id_col", "metadata_cols"}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass
class EventSemantics:
    """A description of what columns mean in event data.

    Maps generic concepts (entity, event, start time, end time)
    to specific column names in a DataFrame. This decouples all
    downstream logic from specific column naming conventions.

    Attributes:
        entity_id_col (str): Column containing entity identifiers.
        event_id_col (str): Column containing event identifiers.
        start_time_col (str): Column containing event start times.
        end_time_col (str): Column containing event end times.
        event_type_col (str | None): Optional column for event types.
        metadata_cols (list[str]): Optional list of extra data columns.
    """

    entity_id_col: str
    start_time_col: str
    end_time_col: str
    event_id_col: str | None = None
    event_type_col: str | None = None
    metadata_cols: list[str] = field(default_factory=list)

    @classmethod
    def build_from_yaml(cls, path: str) -> "EventSemantics":
        """Build semantics from a YAML configuration file.

        Args:
            path: Path to the YAML file.

        Returns:
            A validated EventSemantics instance.

        Raises:
            ValueError: If YAML is missing required fields or has unknown fields.
            TypeError: If field types are wrong.
        """
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        cls._validate_yaml(config, path)
        return cls(**config)

    @staticmethod
    def _validate_yaml(config: dict, path: str) -> None:
        """Validate the structure and types of a YAML config.

        Args:
            config: Parsed YAML dict.
            path: File path for error messages.

        Raises:
            ValueError: If config is not a dict, missing required fields,
                or has unrecognized fields.
            TypeError: If field types are wrong.
        """
        if not isinstance(config, dict):
            raise ValueError(f"YAML at '{path}' must be a mapping, got {type(config).__name__}")

        missing = REQUIRED_FIELDS - config.keys()
        if missing:
            raise ValueError(f"Missing required fields in '{path}': {missing}")

        unknown = config.keys() - ALL_FIELDS
        if unknown:
            raise ValueError(f"Unrecognized fields in '{path}': {unknown}")

        for f in REQUIRED_FIELDS:
            if f in config and not isinstance(config[f], str):
                raise TypeError(f"Field '{f}' in '{path}' must be a string, got {type(config[f]).__name__}")

        if config.get("event_type_col") is not None and not isinstance(config["event_type_col"], str):
            raise TypeError(f"Field 'event_type_col' in '{path}' must be a string or null")

        meta = config.get("metadata_cols")
        if meta is not None:
            if not isinstance(meta, list) or not all(isinstance(m, str) for m in meta):
                raise TypeError(f"Field 'metadata_cols' in '{path}' must be a list of strings")

    def __repr__(self) -> str:
        lines = [
            "EventSemantics",
            f"  entity_id : {self.entity_id_col}",
            f"  event_id  : {self.event_id_col}",
            f"  start_time: {self.start_time_col}",
            f"  end_time  : {self.end_time_col}",
        ]
        if self.event_type_col:
            lines.append(f"  event_type: {self.event_type_col}")
        if self.metadata_cols:
            lines.append(f"  metadata  : {self.metadata_cols}")
        return "\n".join(lines)