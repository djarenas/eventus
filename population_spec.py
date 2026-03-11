"""Population specification.

A PopulationSpec describes what a fake population looks like —
the distributions of continuous covariates and the proportions
of categorical covariates. It does not generate anything. That
is the PopulationGenerator's job.

"I am a description of a population's characteristics."

Built from YAML for reproducibility. Validated on construction.
"""

from dataclasses import dataclass, field
import yaml
import numpy as np


# =====================================================================
#  Registry of supported continuous distributions
# =====================================================================

CONTINUOUS_GENERATORS = {
    "normal": lambda rng, spec, n: rng.normal(
        spec["mean"], spec["std"], n
    ),
    "uniform": lambda rng, spec, n: rng.uniform(
        spec["min"], spec["max"], n
    ),
    "lognormal": lambda rng, spec, n: rng.lognormal(
        spec["mean"], spec["std"], n
    ),
}

# Required parameters for each distribution type
CONTINUOUS_REQUIRED_PARAMS = {
    "normal": {"mean", "std"},
    "uniform": {"min", "max"},
    "lognormal": {"mean", "std"},
}


class PopulationSpec:
    """A description of a population's covariate characteristics.

    Describes how continuous covariates are distributed (e.g.,
    age ~ Normal(50, 15)) and what proportions categorical
    covariates have (e.g., county: Cook 40%, DuPage 20%, ...).

    Does not generate data. That is PopulationGenerator's job.

    Attributes:
        continuous_specs (list[dict]): Specifications for continuous
            covariates. Each dict has 'column', 'distribution', and
            distribution-specific parameters. Optional 'min'/'max'
            for truncation.
        categorical_specs (list[dict]): Specifications for categorical
            covariates. Each dict has 'column' and 'proportions' (a
            dict mapping category names to probabilities).

    Example:
        >>> spec = PopulationSpec(
        ...     continuous_specs=[
        ...         {"column": "age", "distribution": "normal", "mean": 50, "std": 15},
        ...     ],
        ...     categorical_specs=[
        ...         {"column": "county", "proportions": {"Cook": 0.6, "Lake": 0.4}},
        ...     ],
        ... )

    Example (from YAML):
        >>> spec = PopulationSpec.build_from_yaml("population.yaml")
    """

    _ERROR_PREFIX = "[PopulationSpec]"

    # Attribute Declarations
    continuous_specs: list
    categorical_specs: list

    def __init__(self, continuous_specs: list = None, categorical_specs: list = None):
        """Create a population spec and validate it.

        Args:
            continuous_specs: List of continuous covariate specifications.
            categorical_specs: List of categorical covariate specifications.

        Raises:
            TypeError: If specs are wrong types.
            ValueError: If specs are invalid (missing params, bad proportions, etc.)
        """
        self.continuous_specs = continuous_specs or []
        self.categorical_specs = categorical_specs or []
        self._validate()

    @classmethod
    def build_from_yaml(cls, path: str) -> "PopulationSpec":
        """Build a population spec from a YAML file.

        Expected YAML format:
            population:
              continuous:
                - column: age
                  distribution: normal
                  mean: 50
                  std: 15
                  min: 18
                  max: 90
                - column: BMI
                  distribution: normal
                  mean: 27
                  std: 5
              categorical:
                - column: county
                  proportions:
                    Cook: 0.40
                    DuPage: 0.20
                    Lake: 0.15
                    Will: 0.15
                    Kane: 0.10
                - column: gender
                  proportions:
                    M: 0.50
                    F: 0.50

        Args:
            path: Path to the YAML file.

        Returns:
            A validated PopulationSpec.

        Raises:
            TypeError: If path is not a string.
            FileNotFoundError: If file does not exist.
            ValueError: If YAML is malformed.
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

        population = config["population"]
        continuous_specs = population.get("continuous", [])
        categorical_specs = population.get("categorical", [])

        return cls(
            continuous_specs=continuous_specs,
            categorical_specs=categorical_specs,
        )

    @classmethod
    def _validate_yaml_structure(cls, config, path: str) -> None:
        """Validate top-level YAML structure.

        Raises:
            ValueError: If config is not a dict or missing 'population'.
            TypeError: If population is not a dict.
        """
        if not isinstance(config, dict):
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must be a dictionary, "
                f"got {type(config).__name__}"
            )
        if "population" not in config:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must have a 'population' key. "
                f"Found keys: {list(config.keys())}"
            )
        if not isinstance(config["population"], dict):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'population' in '{path}' must be a dictionary, "
                f"got {type(config['population']).__name__}"
            )

    # ---- Validation ----

    def _validate(self) -> None:
        """Validate all specs after construction."""
        self._validate_continuous_specs()
        self._validate_categorical_specs()
        self._validate_no_duplicate_columns()

    def _validate_continuous_specs(self) -> None:
        """Validate continuous covariate specifications.

        Checks:
            - Each spec is a dict with 'column' and 'distribution'
            - Distribution type is in CONTINUOUS_GENERATORS registry
            - Required parameters for the distribution are present
            - min < max if both specified
            - Numeric values are actually numeric

        Raises:
            TypeError: If specs are wrong types.
            ValueError: If specs are invalid.
        """
        if not isinstance(self.continuous_specs, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"continuous_specs must be a list, "
                f"got {type(self.continuous_specs).__name__}"
            )

        for i, spec in enumerate(self.continuous_specs):
            prefix = f"{self._ERROR_PREFIX} validate: continuous_specs[{i}]"

            if not isinstance(spec, dict):
                raise TypeError(f"{prefix} must be a dict, got {type(spec).__name__}")

            if "column" not in spec:
                raise ValueError(f"{prefix} missing 'column' key")
            if not isinstance(spec["column"], str):
                raise TypeError(
                    f"{prefix} 'column' must be a string, "
                    f"got {type(spec['column']).__name__}"
                )

            if "distribution" not in spec:
                raise ValueError(f"{prefix} missing 'distribution' key")
            if spec["distribution"] not in CONTINUOUS_GENERATORS:
                raise ValueError(
                    f"{prefix} unknown distribution '{spec['distribution']}'. "
                    f"Available: {list(CONTINUOUS_GENERATORS.keys())}"
                )

            # Check required parameters for this distribution type
            dist_type = spec["distribution"]
            required = CONTINUOUS_REQUIRED_PARAMS[dist_type]
            missing = required - set(spec.keys())
            if missing:
                raise ValueError(
                    f"{prefix} distribution '{dist_type}' requires "
                    f"parameters {required}, missing: {missing}"
                )

            # Validate numeric values
            for param in required:
                if not isinstance(spec[param], (int, float)):
                    raise TypeError(
                        f"{prefix} parameter '{param}' must be numeric, "
                        f"got {type(spec[param]).__name__}"
                    )

            # Validate min/max if present
            if "min" in spec and "max" in spec:
                if spec["min"] >= spec["max"]:
                    raise ValueError(
                        f"{prefix} 'min' ({spec['min']}) must be less than "
                        f"'max' ({spec['max']})"
                    )

            # Validate std > 0 for normal and lognormal
            if dist_type in ("normal", "lognormal"):
                if spec["std"] <= 0:
                    raise ValueError(
                        f"{prefix} 'std' must be positive, got {spec['std']}"
                    )

    def _validate_categorical_specs(self) -> None:
        """Validate categorical covariate specifications.

        Checks:
            - Each spec is a dict with 'column' and 'proportions'
            - Proportions is a dict mapping names to probabilities
            - All proportions are non-negative
            - Proportions sum to 1 (within tolerance)

        Raises:
            TypeError: If specs are wrong types.
            ValueError: If specs are invalid.
        """
        if not isinstance(self.categorical_specs, list):
            raise TypeError(
                f"{self._ERROR_PREFIX} validate: "
                f"categorical_specs must be a list, "
                f"got {type(self.categorical_specs).__name__}"
            )

        for i, spec in enumerate(self.categorical_specs):
            prefix = f"{self._ERROR_PREFIX} validate: categorical_specs[{i}]"

            if not isinstance(spec, dict):
                raise TypeError(f"{prefix} must be a dict, got {type(spec).__name__}")

            if "column" not in spec:
                raise ValueError(f"{prefix} missing 'column' key")
            if not isinstance(spec["column"], str):
                raise TypeError(
                    f"{prefix} 'column' must be a string, "
                    f"got {type(spec['column']).__name__}"
                )

            if "proportions" not in spec:
                raise ValueError(f"{prefix} missing 'proportions' key")
            if not isinstance(spec["proportions"], dict):
                raise TypeError(
                    f"{prefix} 'proportions' must be a dict, "
                    f"got {type(spec['proportions']).__name__}"
                )
            if len(spec["proportions"]) == 0:
                raise ValueError(f"{prefix} 'proportions' cannot be empty")

            # Validate proportion values
            total = 0
            for category, proportion in spec["proportions"].items():
                if not isinstance(proportion, (int, float)):
                    raise TypeError(
                        f"{prefix} proportion for '{category}' must be numeric, "
                        f"got {type(proportion).__name__}"
                    )
                if proportion < 0:
                    raise ValueError(
                        f"{prefix} proportion for '{category}' cannot be negative, "
                        f"got {proportion}"
                    )
                total += proportion

            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"{prefix} proportions must sum to 1.0, got {total:.6f}"
                )

    def _validate_no_duplicate_columns(self) -> None:
        """Check no column name appears more than once.

        Raises:
            ValueError: If duplicate column names found.
        """
        all_cols = self.all_column_names()
        duplicates = set(c for c in all_cols if all_cols.count(c) > 1)
        if duplicates:
            raise ValueError(
                f"{self._ERROR_PREFIX} validate: "
                f"Duplicate column names: {duplicates}"
            )

    # ---- Accessors ----

    def all_column_names(self) -> list:
        """Return a flat list of all covariate column names.

        Returns:
            List of column name strings.
        """
        cols = []
        cols.extend(spec["column"] for spec in self.continuous_specs)
        cols.extend(spec["column"] for spec in self.categorical_specs)
        return cols

    def continuous_columns(self) -> list:
        """Return list of continuous column names.

        Returns:
            List of column name strings.
        """
        return [spec["column"] for spec in self.continuous_specs]

    def categorical_columns(self) -> list:
        """Return list of categorical column names.

        Returns:
            List of column name strings.
        """
        return [spec["column"] for spec in self.categorical_specs]

    def get_spec_for_column(self, column: str) -> dict:
        """Look up the full spec for a specific column.

        Args:
            column: Column name.

        Returns:
            The spec dict for that column.

        Raises:
            KeyError: If column not found.
        """
        for spec in self.continuous_specs:
            if spec["column"] == column:
                return spec
        for spec in self.categorical_specs:
            if spec["column"] == column:
                return spec
        raise KeyError(
            f"{self._ERROR_PREFIX} get_spec_for_column: "
            f"'{column}' not found. "
            f"Available: {self.all_column_names()}"
        )

    def describe(self) -> list:
        """Describe this population in plain language.

        Returns:
            List of descriptive strings.
        """
        lines = ["PopulationSpec"]

        if self.continuous_specs:
            lines.append("  Continuous covariates:")
            for spec in self.continuous_specs:
                dist = spec["distribution"]
                col = spec["column"]
                if dist == "normal":
                    desc = f"Normal(mean={spec['mean']}, std={spec['std']})"
                elif dist == "uniform":
                    desc = f"Uniform(min={spec['min']}, max={spec['max']})"
                elif dist == "lognormal":
                    desc = f"LogNormal(mean={spec['mean']}, std={spec['std']})"
                else:
                    desc = dist

                bounds = ""
                if "min" in spec and dist != "uniform":
                    bounds += f", min={spec['min']}"
                if "max" in spec and dist != "uniform":
                    bounds += f", max={spec['max']}"

                lines.append(f"    {col}: {desc}{bounds}")

        if self.categorical_specs:
            lines.append("  Categorical covariates:")
            for spec in self.categorical_specs:
                col = spec["column"]
                props = ", ".join(
                    f"{k}={v*100:.0f}%"
                    for k, v in spec["proportions"].items()
                )
                lines.append(f"    {col}: {props}")

        return lines

    def to_dict(self) -> dict:
        """Export as a plain dictionary for YAML serialization.

        Returns:
            Dict matching the YAML format.
        """
        return {
            "population": {
                "continuous": [dict(s) for s in self.continuous_specs],
                "categorical": [dict(s) for s in self.categorical_specs],
            }
        }

    # ---- Dunder methods ----

    def __repr__(self) -> str:
        n_cont = len(self.continuous_specs)
        n_cat = len(self.categorical_specs)
        return (
            f"PopulationSpec("
            f"{n_cont} continuous, "
            f"{n_cat} categorical)"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, PopulationSpec):
            return False
        return (self.continuous_specs == other.continuous_specs
                and self.categorical_specs == other.categorical_specs)
