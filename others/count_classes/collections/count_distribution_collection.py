"""Count distribution collection.

A collection is a validated group of distributions with parameters.
It knows how to simulate from each of them using the correct
simulator, and can describe all of them.

A collection can be built from:
    - menu.fit_all() output (dict)
    - a YAML file of distributions with parameters
    - direct dict construction

A collection can save itself to YAML, and that YAML can be
loaded back to recreate the exact same collection. This enables
reproducible simulation studies.
"""

import numpy as np
import yaml

from .count_distributions import CountDistribution
from .model_registry import MODEL_REGISTRY, DISTRIBUTION_TO_MODEL


# Reverse lookup: distribution class name string → model name
_CLASS_NAME_TO_MODEL = {
    entry["distribution"].__name__: model_name
    for model_name, entry in MODEL_REGISTRY.items()
}


class CountDistributionCollection:
    """A validated group of distributions with parameters.

    Holds named distributions and can simulate from any or all
    of them. Knows how to pair each distribution with its
    simulator via the model registry.

    Can save to YAML and load from YAML for reproducibility.

    Attributes:
        distributions (dict): Maps name to CountDistribution instance.

    Example (from fitting):
        >>> fitted = menu.fit_all(counts)
        >>> collection = CountDistributionCollection(fitted)

    Example (save and load):
        >>> collection.save_to_yaml("fitted_models.yaml")
        >>> loaded = CountDistributionCollection.build_from_yaml("fitted_models.yaml")

    Example (simulate):
        >>> simulated = collection.simulate_all(n=500)
    """

    _ERROR_PREFIX = "[CountDistributionCollection]"

    # Attribute Declarations
    distributions: dict

    def __init__(self, distributions: dict):
        """Create a collection from a dict of distributions.

        Validates that all values are CountDistribution instances
        and that each distribution type is known in the model registry.

        Args:
            distributions: Dict mapping names to CountDistribution
                instances. e.g. {"Poisson": PoissonDistribution(...)}

        Raises:
            TypeError: If distributions is not a dict or values
                are not CountDistribution instances.
            ValueError: If distributions is empty or a distribution
                type is not in the model registry.
        """
        self._validate(distributions)
        self.distributions = distributions

    @classmethod
    def build_from_yaml(cls, path: str) -> "CountDistributionCollection":
        """Load a collection from a YAML file.

        Expected YAML format (produced by save_to_yaml):
            distributions:
              - distribution: PoissonDistribution
                parameters:
                  lambda: 4.2200
              - distribution: PoissonGammaDistribution
                parameters:
                  alpha: 3.0145
                  beta: 0.7123

        Each entry's distribution type is looked up in the model
        registry to determine the model name (used as dict key)
        and to validate that the distribution type is known.

        Args:
            path: Path to the YAML file.

        Returns:
            A validated CountDistributionCollection.

        Raises:
            TypeError: If path is not a string.
            FileNotFoundError: If the file does not exist.
            ValueError: If YAML is malformed or contains unknown
                distribution types.
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

        cls._validate_yaml(config, path)

        distributions = {}
        for i, entry in enumerate(config["distributions"]):
            # Validate entry structure
            if not isinstance(entry, dict):
                raise TypeError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"Entry {i} in '{path}' must be a dict, "
                    f"got {type(entry).__name__}"
                )
            if "distribution" not in entry:
                raise ValueError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"Entry {i} in '{path}' missing 'distribution' key"
                )
            if "parameters" not in entry:
                raise ValueError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"Entry {i} in '{path}' missing 'parameters' key"
                )

            # Look up distribution class
            dist_class_name = entry["distribution"]
            if dist_class_name not in _CLASS_NAME_TO_MODEL:
                raise ValueError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"Unknown distribution type '{dist_class_name}' "
                    f"in entry {i} of '{path}'. "
                    f"Known types: {list(_CLASS_NAME_TO_MODEL.keys())}"
                )

            # Get model name and distribution class
            model_name = _CLASS_NAME_TO_MODEL[dist_class_name]
            dist_class = MODEL_REGISTRY[model_name]["distribution"]

            # Create distribution (validates params automatically)
            params = entry["parameters"]
            dist = dist_class(params)

            distributions[model_name] = dist

        return cls(distributions)

    @classmethod
    def _validate_yaml(cls, config, path: str) -> None:
        """Validate the top-level YAML structure.

        Raises:
            ValueError: If config is not a dict or missing 'distributions'.
            TypeError: If distributions is not a list.
        """
        if not isinstance(config, dict):
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must be a dictionary, "
                f"got {type(config).__name__}"
            )
        if "distributions" not in config:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must have a 'distributions' key. "
                f"Found keys: {list(config.keys())}"
            )
        if not isinstance(config["distributions"], list):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'distributions' in '{path}' must be a list, "
                f"got {type(config['distributions']).__name__}"
            )
        if len(config["distributions"]) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'distributions' list in '{path}' cannot be empty"
            )

    def save_to_yaml(self, path: str) -> None:
        """Save the collection to a YAML file.

        Produces a YAML file that can be loaded back with
        build_from_yaml() to recreate the exact same collection.

        Args:
            path: File path to save to.

        Raises:
            TypeError: If path is not a string.
            RuntimeError: If writing fails.
        """
        if not isinstance(path, str):
            raise TypeError(
                f"{self._ERROR_PREFIX} save_to_yaml: "
                f"path must be a string, got {type(path).__name__}"
            )

        entries = []
        for name, dist in self.distributions.items():
            entries.append(dist.to_dict())

        output = {"distributions": entries}

        try:
            with open(path, "w") as f:
                yaml.dump(output, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise RuntimeError(
                f"{self._ERROR_PREFIX} save_to_yaml: "
                f"Failed to write to '{path}': {e}"
            )

    def _validate(self, distributions) -> None:
        """Validate the distributions dict.

        Raises:
            TypeError: If not a dict or values are wrong type.
            ValueError: If empty or unknown distribution type.
        """
        if not isinstance(distributions, dict):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected dict, got {type(distributions).__name__}"
            )
        if len(distributions) == 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Distributions dict cannot be empty"
            )
        for name, dist in distributions.items():
            if not isinstance(name, str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Distribution name must be a string, "
                    f"got {type(name).__name__} for key {name}"
                )
            if not isinstance(dist, CountDistribution):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Distribution '{name}' is not a CountDistribution, "
                    f"got {type(dist).__name__}"
                )
            if type(dist) not in DISTRIBUTION_TO_MODEL:
                raise ValueError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Distribution type '{type(dist).__name__}' for '{name}' "
                    f"is not in the model registry. "
                    f"Known types: {list(DISTRIBUTION_TO_MODEL.keys())}"
                )

    def _get_simulator(self, distribution: CountDistribution):
        """Look up and create the right simulator for a distribution.

        Args:
            distribution: A CountDistribution instance.

        Returns:
            A simulator instance paired with the distribution.

        Raises:
            KeyError: If distribution type is not in the registry.
        """
        model_name = DISTRIBUTION_TO_MODEL[type(distribution)]
        simulator_class = MODEL_REGISTRY[model_name]["simulator"]
        return simulator_class(distribution)

    # ---- Simulation ----

    def simulate_one(self, name: str, n: int) -> np.ndarray:
        """Simulate counts from a single named distribution.

        Args:
            name: Name of the distribution in the collection.
            n: Number of counts to generate.

        Returns:
            Array of n non-negative integer counts.

        Raises:
            KeyError: If name is not in the collection.
            ValueError: If n is not positive.
        """
        if name not in self.distributions:
            raise KeyError(
                f"{self._ERROR_PREFIX} simulate_one: "
                f"'{name}' not in collection. "
                f"Available: {list(self.distributions.keys())}"
            )
        if not isinstance(n, int) or n <= 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} simulate_one: "
                f"n must be a positive integer, got {n}"
            )

        dist = self.distributions[name]
        simulator = self._get_simulator(dist)
        return simulator.simulate_counts(n)

    def simulate_all(self, n) -> dict:
        """Simulate counts from all distributions in the collection.

        If n is a single integer, returns one array per distribution.
        If n is a list of integers, returns a dict of arrays per
        distribution, keyed by sample size.

        Args:
            n: Single int or list of ints for sample sizes.

        Returns:
            If n is int:
                dict[str, np.ndarray]

            If n is list:
                dict[str, dict[int, np.ndarray]]

        Raises:
            TypeError: If n is not int or list of ints.
            ValueError: If any sample size is not positive.
        """
        if isinstance(n, int):
            return self._simulate_all_single(n)
        elif isinstance(n, list):
            return self._simulate_all_multiple(n)
        else:
            raise TypeError(
                f"{self._ERROR_PREFIX} simulate_all: "
                f"n must be int or list of ints, got {type(n).__name__}"
            )

    def _simulate_all_single(self, n: int) -> dict:
        """Simulate all distributions at a single sample size."""
        if n <= 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} simulate_all: "
                f"n must be positive, got {n}"
            )

        results = {}
        for name, dist in self.distributions.items():
            simulator = self._get_simulator(dist)
            results[name] = simulator.simulate_counts(n)
        return results

    def _simulate_all_multiple(self, n_list: list) -> dict:
        """Simulate all distributions at multiple sample sizes."""
        for n in n_list:
            if not isinstance(n, int) or n <= 0:
                raise ValueError(
                    f"{self._ERROR_PREFIX} simulate_all: "
                    f"All sample sizes must be positive integers, got {n}"
                )

        results = {}
        for name, dist in self.distributions.items():
            simulator = self._get_simulator(dist)
            results[name] = {}
            for n in n_list:
                results[name][n] = simulator.simulate_counts(n)
        return results

    # ---- Description ----

    def describe_all(self) -> dict:
        """Get plain-language descriptions from all distributions.

        Returns:
            Dict mapping name to list of description strings.
        """
        return {
            name: dist.describe()
            for name, dist in self.distributions.items()
        }

    # ---- Access ----

    def get(self, name: str) -> CountDistribution:
        """Retrieve a single distribution by name.

        Args:
            name: Distribution name.

        Returns:
            The CountDistribution instance.

        Raises:
            KeyError: If name is not in the collection.
        """
        if name not in self.distributions:
            raise KeyError(
                f"{self._ERROR_PREFIX} get: "
                f"'{name}' not in collection. "
                f"Available: {list(self.distributions.keys())}"
            )
        return self.distributions[name]

    def names(self) -> list:
        """Return list of all distribution names.

        Returns:
            List of name strings.
        """
        return list(self.distributions.keys())

    # ---- Dunder methods ----

    def __iter__(self):
        """Iterate over (name, distribution) pairs."""
        return iter(self.distributions.items())

    def __len__(self) -> int:
        """Number of distributions in the collection."""
        return len(self.distributions)

    def __contains__(self, name: str) -> bool:
        """Check if a name is in the collection."""
        return name in self.distributions

    def __repr__(self) -> str:
        names = list(self.distributions.keys())
        return f"CountDistributionCollection({len(names)} distributions: {names})"
