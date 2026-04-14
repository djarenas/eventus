"""Covariate semantics.

CovariateSemantics describes what covariate columns exist in a
dataset, what type they are (continuous or categorical), whether
they are person-level or event-level, and how event-level
covariates should be aggregated to person-level for regression.

It does not hold data. It describes data. Same pattern as
EventSemantics.
"""

from dataclasses import dataclass, field
import yaml


VALID_CONTINUOUS_AGGREGATIONS = {"mean", "sum", "min", "max", "median"}
VALID_CATEGORICAL_AGGREGATIONS = {"mode", "proportion"}
VALID_AGGREGATIONS = VALID_CONTINUOUS_AGGREGATIONS | VALID_CATEGORICAL_AGGREGATIONS


@dataclass
class CovariateSemantics:
    """A description of covariate columns in event data.

    Maps column names to their types (continuous/categorical),
    levels (person/event), aggregation strategies, and interaction
    terms. Used by EventsWithCovariates to validate data and by
    regression fitters to build design matrices.

    Attributes:
        person_id_col (str): Column containing person identifiers.
            Must match the person_id_col in EventSemantics.
        person_level_continuous (list[str]): Continuous covariates
            that are constant per person (e.g., age, BMI).
        person_level_categorical (list[str]): Categorical covariates
            that are constant per person (e.g., county, gender).
        event_level_continuous (list[dict]): Continuous covariates
            that vary per event. Each dict has 'column' and
            'aggregation' keys. e.g., {"column": "wait_time", "aggregation": "mean"}
        event_level_categorical (list[dict]): Categorical covariates
            that vary per event. Each dict has 'column' and
            'aggregation' keys. e.g., {"column": "was_emergency", "aggregation": "proportion"}
        interactions (list[tuple]): Pairs of column names to
            create interaction terms. e.g., [("age", "BMI")]

    Example:
        >>> sem = CovariateSemantics(
        ...     person_id_col="patient_id",
        ...     person_level_continuous=["age", "BMI"],
        ...     person_level_categorical=["county"],
        ...     event_level_continuous=[{"column": "wait_time", "aggregation": "mean"}],
        ...     event_level_categorical=[{"column": "was_emergency", "aggregation": "proportion"}],
        ...     interactions=[("age", "BMI")],
        ... )

    Example (from YAML):
        >>> sem = CovariateSemantics.build_from_yaml("covariates.yaml")
    """

    _ERROR_PREFIX = "[CovariateSemantics]"

    person_id_col: str
    person_level_continuous: list = field(default_factory=list)
    person_level_categorical: list = field(default_factory=list)
    event_level_continuous: list = field(default_factory=list)
    event_level_categorical: list = field(default_factory=list)
    interactions: list = field(default_factory=list)

    def __post_init__(self):
        """Validate immediately after construction."""
        self._validate()

    @classmethod
    def build_from_yaml(cls, path: str) -> "CovariateSemantics":
        """Build covariate semantics from a YAML file.

        Expected YAML format:
            person_id_col: patient_id
            person_level:
              continuous:
                - age
                - BMI
              categorical:
                - county
                - gender
            event_level:
              continuous:
                - column: wait_time
                  aggregation: mean
                - column: cost
                  aggregation: sum
              categorical:
                - column: was_emergency
                  aggregation: proportion
                - column: day_of_week
                  aggregation: mode
            interactions:
              - [age, BMI]
              - [age, county]

        Args:
            path: Path to the YAML file.

        Returns:
            A validated CovariateSemantics instance.

        Raises:
            TypeError: If path is not a string.
            FileNotFoundError: If the file does not exist.
            ValueError: If YAML is malformed or invalid.
        """
        if not isinstance(path, str):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"path must be a string, got {type(path).__name__}"
            )

        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"File not found: '{path}'"
            )
        except yaml.YAMLError as e:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Failed to parse YAML at '{path}': {e}"
            )

        cls._validate_yaml_structure(config, path)

        # Extract person_id_col
        person_id_col = config["person_id_col"]

        # Extract person-level covariates
        person_level = config.get("person_level", {})
        person_level_continuous = person_level.get("continuous", [])
        person_level_categorical = person_level.get("categorical", [])

        # Extract event-level covariates
        event_level = config.get("event_level", {})
        event_level_continuous = event_level.get("continuous", [])
        event_level_categorical = event_level.get("categorical", [])

        # Extract interactions
        interactions_raw = config.get("interactions", [])
        interactions = [tuple(pair) for pair in interactions_raw]

        return cls(
            person_id_col=person_id_col,
            person_level_continuous=person_level_continuous,
            person_level_categorical=person_level_categorical,
            event_level_continuous=event_level_continuous,
            event_level_categorical=event_level_categorical,
            interactions=interactions,
        )

    @classmethod
    def _validate_yaml_structure(cls, config, path: str) -> None:
        """Validate the top-level YAML structure.

        Raises:
            ValueError: If config is not a dict or missing required keys.
            TypeError: If values are wrong types.
        """
        if not isinstance(config, dict):
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must be a dictionary, "
                f"got {type(config).__name__}"
            )
        if "person_id_col" not in config:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must have a 'person_id_col' key"
            )
        if not isinstance(config["person_id_col"], str):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'person_id_col' in '{path}' must be a string, "
                f"got {type(config['person_id_col']).__name__}"
            )

        # Validate person_level structure if present
        if "person_level" in config:
            pl = config["person_level"]
            if not isinstance(pl, dict):
                raise TypeError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"'person_level' in '{path}' must be a dictionary, "
                    f"got {type(pl).__name__}"
                )

        # Validate event_level structure if present
        if "event_level" in config:
            el = config["event_level"]
            if not isinstance(el, dict):
                raise TypeError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"'event_level' in '{path}' must be a dictionary, "
                    f"got {type(el).__name__}"
                )

        # Validate interactions structure if present
        if "interactions" in config:
            interactions = config["interactions"]
            if not isinstance(interactions, list):
                raise TypeError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"'interactions' in '{path}' must be a list, "
                    f"got {type(interactions).__name__}"
                )

    def _validate(self) -> None:
        """Validate all fields after construction.

        Checks types, duplicates, aggregation methods, and
        interaction term references.

        Raises:
            TypeError: If fields are wrong types.
            ValueError: If duplicates, invalid aggregations, or
                bad interaction references.
        """
        self._validate_person_id_col()
        self._validate_person_level_continuous()
        self._validate_person_level_categorical()
        self._validate_event_level_continuous()
        self._validate_event_level_categorical()
        self._validate_no_duplicate_columns()
        self._validate_interactions()

    def _validate_person_id_col(self) -> None:
        """Check person_id_col is a non-empty string."""
        if not isinstance(self.person_id_col, str):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"person_id_col must be a string, "
                f"got {type(self.person_id_col).__name__}"
            )
        if len(self.person_id_col) == 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} validate: "
                f"person_id_col cannot be empty"
            )

    def _validate_person_level_continuous(self) -> None:
        """Check person-level continuous columns are strings."""
        if not isinstance(self.person_level_continuous, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"person_level_continuous must be a list, "
                f"got {type(self.person_level_continuous).__name__}"
            )
        for i, col in enumerate(self.person_level_continuous):
            if not isinstance(col, str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"person_level_continuous[{i}] must be a string, "
                    f"got {type(col).__name__}"
                )

    def _validate_person_level_categorical(self) -> None:
        """Check person-level categorical columns are strings."""
        if not isinstance(self.person_level_categorical, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"person_level_categorical must be a list, "
                f"got {type(self.person_level_categorical).__name__}"
            )
        for i, col in enumerate(self.person_level_categorical):
            if not isinstance(col, str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"person_level_categorical[{i}] must be a string, "
                    f"got {type(col).__name__}"
                )

    def _validate_event_level_continuous(self) -> None:
        """Check event-level continuous entries have column and valid aggregation."""
        if not isinstance(self.event_level_continuous, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"event_level_continuous must be a list, "
                f"got {type(self.event_level_continuous).__name__}"
            )
        for i, entry in enumerate(self.event_level_continuous):
            if not isinstance(entry, dict):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_continuous[{i}] must be a dict, "
                    f"got {type(entry).__name__}"
                )
            if "column" not in entry:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_continuous[{i}] missing 'column' key"
                )
            if "aggregation" not in entry:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_continuous[{i}] missing 'aggregation' key"
                )
            if not isinstance(entry["column"], str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_continuous[{i}]['column'] must be a string, "
                    f"got {type(entry['column']).__name__}"
                )
            if entry["aggregation"] not in VALID_CONTINUOUS_AGGREGATIONS:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_continuous[{i}] has invalid aggregation "
                    f"'{entry['aggregation']}'. "
                    f"Valid options: {VALID_CONTINUOUS_AGGREGATIONS}"
                )

    def _validate_event_level_categorical(self) -> None:
        """Check event-level categorical entries have column and valid aggregation."""
        if not isinstance(self.event_level_categorical, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"event_level_categorical must be a list, "
                f"got {type(self.event_level_categorical).__name__}"
            )
        for i, entry in enumerate(self.event_level_categorical):
            if not isinstance(entry, dict):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_categorical[{i}] must be a dict, "
                    f"got {type(entry).__name__}"
                )
            if "column" not in entry:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_categorical[{i}] missing 'column' key"
                )
            if "aggregation" not in entry:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_categorical[{i}] missing 'aggregation' key"
                )
            if not isinstance(entry["column"], str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_categorical[{i}]['column'] must be a string, "
                    f"got {type(entry['column']).__name__}"
                )
            if entry["aggregation"] not in VALID_CATEGORICAL_AGGREGATIONS:
                raise ValueError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"event_level_categorical[{i}] has invalid aggregation "
                    f"'{entry['aggregation']}'. "
                    f"Valid options: {VALID_CATEGORICAL_AGGREGATIONS}"
                )

    def _validate_no_duplicate_columns(self) -> None:
        """Check that no column name appears in more than one place."""
        all_cols = self.all_column_names()
        duplicates = set(c for c in all_cols if all_cols.count(c) > 1)
        if duplicates:
            raise ValueError(
                f"{self._ERROR_PREFIX} validate: "
                f"Duplicate column names found across covariate levels: {duplicates}"
            )

    def _validate_interactions(self) -> None:
        """Check that interaction terms reference existing columns."""
        if not isinstance(self.interactions, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"interactions must be a list, "
                f"got {type(self.interactions).__name__}"
            )
        all_cols = set(self.all_column_names())
        for i, pair in enumerate(self.interactions):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError(
                    f"{self._ERROR_PREFIX} validate: "
                    f"interactions[{i}] must be a tuple of 2 column names, "
                    f"got {pair}"
                )
            for col in pair:
                if not isinstance(col, str):
                    raise TypeError(
                        f"{self._ERROR_PREFIX} validate: "
                        f"interactions[{i}] contains non-string: {col}"
                    )
                if col not in all_cols:
                    raise ValueError(
                        f"{self._ERROR_PREFIX} validate: "
                        f"interactions[{i}] references unknown column '{col}'. "
                        f"Available columns: {all_cols}"
                    )

    # ---- Accessors ----

    def all_column_names(self) -> list:
        """Return a flat list of all covariate column names.

        Includes person-level and event-level columns but not
        person_id_col.

        Returns:
            List of column name strings.
        """
        cols = []
        cols.extend(self.person_level_continuous)
        cols.extend(self.person_level_categorical)
        cols.extend(e["column"] for e in self.event_level_continuous)
        cols.extend(e["column"] for e in self.event_level_categorical)
        return cols

    def person_level_columns(self) -> list:
        """Return all person-level covariate column names.

        Returns:
            List of column name strings.
        """
        return self.person_level_continuous + self.person_level_categorical

    def event_level_columns(self) -> list:
        """Return all event-level covariate column names.

        Returns:
            List of column name strings.
        """
        cols = []
        cols.extend(e["column"] for e in self.event_level_continuous)
        cols.extend(e["column"] for e in self.event_level_categorical)
        return cols

    def get_aggregation(self, column: str) -> str:
        """Look up the aggregation method for an event-level column.

        Args:
            column: Event-level column name.

        Returns:
            Aggregation method string (e.g., "mean", "proportion").

        Raises:
            KeyError: If column is not an event-level covariate.
        """
        for entry in self.event_level_continuous:
            if entry["column"] == column:
                return entry["aggregation"]
        for entry in self.event_level_categorical:
            if entry["column"] == column:
                return entry["aggregation"]
        raise KeyError(
            f"{self._ERROR_PREFIX} get_aggregation: "
            f"'{column}' is not an event-level covariate. "
            f"Event-level columns: {self.event_level_columns()}"
        )

    # ---- Dunder methods ----

    def __repr__(self) -> str:
        lines = [
            "CovariateSemantics",
            f"  person_id    : {self.person_id_col}",
        ]
        if self.person_level_continuous:
            lines.append(f"  person continuous: {self.person_level_continuous}")
        if self.person_level_categorical:
            lines.append(f"  person categorical: {self.person_level_categorical}")
        if self.event_level_continuous:
            event_cont = [f"{e['column']}({e['aggregation']})" for e in self.event_level_continuous]
            lines.append(f"  event continuous: {event_cont}")
        if self.event_level_categorical:
            event_cat = [f"{e['column']}({e['aggregation']})" for e in self.event_level_categorical]
            lines.append(f"  event categorical: {event_cat}")
        if self.interactions:
            lines.append(f"  interactions: {self.interactions}")
        return "\n".join(lines)
