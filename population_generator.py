"""Population generator.

A PopulationGenerator generates a fake covariates DataFrame from
a PopulationSpec. It creates synthetic people with realistic
covariate distributions for simulation studies.

"I generate fake people based on a population description."

Uses the CONTINUOUS_GENERATORS registry from PopulationSpec to
avoid elif chains. Adding a new distribution type requires only
adding one entry to the registry.
"""

import numpy as np
import pandas as pd

from .population_spec import PopulationSpec, CONTINUOUS_GENERATORS


class PopulationGenerator:
    """Generates a fake covariates DataFrame from a PopulationSpec.

    Takes a population specification and produces a DataFrame with
    one row per person. Continuous covariates are drawn from the
    specified distributions. Categorical covariates are sampled
    from the specified proportions. A person_id column is
    automatically added.

    Attributes:
        population_spec (PopulationSpec): The population description
            to generate from.

    Example:
        >>> spec = PopulationSpec.build_from_yaml("population.yaml")
        >>> generator = PopulationGenerator(spec)
        >>> df = generator.generate(n=500)
        >>> df.head()
           person_id   age   BMI  county gender  previous_diagnosis
        0          0  52.3  28.1    Cook      M                   0
        1          1  34.7  22.5    Lake      F                   1

    Example (reproducible):
        >>> df = generator.generate(n=500, seed=42)
    """

    _ERROR_PREFIX = "[PopulationGenerator]"

    # Attribute Declarations
    population_spec: PopulationSpec

    def __init__(self, population_spec: PopulationSpec):
        """Create a generator for the given population spec.

        Args:
            population_spec: A validated PopulationSpec.

        Raises:
            TypeError: If population_spec is not a PopulationSpec.
        """
        if not isinstance(population_spec, PopulationSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected PopulationSpec, got {type(population_spec).__name__}"
            )
        self.population_spec = population_spec

    def generate(self, n: int, seed: int = None) -> pd.DataFrame:
        """Generate a fake covariates DataFrame.

        Creates n synthetic people with covariates drawn from the
        distributions and proportions specified in the population spec.
        Adds a person_id column starting from 0.

        Args:
            n: Number of people to generate. Must be positive.
            seed: Optional random seed for reproducibility.

        Returns:
            DataFrame with one row per person, columns for person_id
            and all covariates in the population spec.

        Raises:
            TypeError: If n is not an integer.
            ValueError: If n is not positive.
        """
        if not isinstance(n, int):
            raise TypeError(
                f"{self._ERROR_PREFIX} generate: "
                f"n must be an integer, got {type(n).__name__}"
            )
        if n <= 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} generate: "
                f"n must be positive, got {n}"
            )

        rng = np.random.default_rng(seed)
        data = {"person_id": np.arange(n)}

        # Generate continuous covariates
        for spec in self.population_spec.continuous_specs:
            values = self._generate_continuous(rng, spec, n)
            data[spec["column"]] = values

        # Generate categorical covariates
        for spec in self.population_spec.categorical_specs:
            values = self._generate_categorical(rng, spec, n)
            data[spec["column"]] = values

        return pd.DataFrame(data)

    def _generate_continuous(self, rng, spec: dict, n: int) -> np.ndarray:
        """Generate values for one continuous covariate.

        Uses the CONTINUOUS_GENERATORS registry to look up the
        right generation function. Applies min/max truncation
        if specified.

        Args:
            rng: Numpy random generator.
            spec: Covariate specification dict.
            n: Number of values to generate.

        Returns:
            Array of n float values.
        """
        dist_type = spec["distribution"]
        generator_fn = CONTINUOUS_GENERATORS[dist_type]
        values = generator_fn(rng, spec, n)

        # Apply truncation if min/max specified
        if "min" in spec:
            values = np.clip(values, spec["min"], None)
        if "max" in spec:
            values = np.clip(values, None, spec["max"])

        return np.round(values, 2)

    def _generate_categorical(self, rng, spec: dict, n: int) -> np.ndarray:
        """Generate values for one categorical covariate.

        Samples categories according to the specified proportions.

        Args:
            rng: Numpy random generator.
            spec: Covariate specification dict with 'proportions'.
            n: Number of values to generate.

        Returns:
            Array of n category values.
        """
        categories = list(spec["proportions"].keys())
        probabilities = list(spec["proportions"].values())
        return rng.choice(categories, size=n, p=probabilities)

    def describe(self) -> list:
        """Describe this generator in plain language.

        Returns:
            List of descriptive strings.
        """
        lines = ["PopulationGenerator"]
        lines.extend(f"  {line}" for line in self.population_spec.describe()[1:])
        return lines

    def __repr__(self) -> str:
        return f"PopulationGenerator({self.population_spec})"
