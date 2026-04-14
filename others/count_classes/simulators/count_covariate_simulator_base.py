"""Count covariate simulator base class.

A covariate simulator generates fake count data for a population
where counts depend on covariates. It combines a covariate
distribution (how covariates affect counts) with a population
generator (what the population looks like).

"I generate fake count data for a population where counts
depend on covariates."

Each subclass implements _draw_counts() to handle the specific
count-generating process (Poisson, PoissonGamma, ZIP, etc.).
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

from .distributions.count_covariate_distributions import CountCovariateDistribution
from .events.population_generator import PopulationGenerator
from .helper_count_design_matrix_preparer import build_design_matrix_dataframe


class CountCovariateSimulator(ABC):
    """Base class for all count covariate simulators.

    A covariate simulator holds a distribution (how covariates
    affect counts) and a population generator (what the population
    looks like). Together they have everything needed to simulate
    realistic count data.

    Attributes:
        distribution (CountCovariateDistribution): The covariate
            distribution with coefficients.
        generator (PopulationGenerator): The population generator
            with a PopulationSpec.

    Example:
        >>> simulator = PoissonCovariateSimulator(distribution, generator)
        >>> result = simulator.simulate(n=500, seed=42)
        >>> result.head()
           person_id  age   BMI  county  gender  event_count
        0          0   52  28.1    Cook       M            3
        1          1   34  22.5  DuPage       F            7
    """

    _ERROR_PREFIX = "[CountCovariateSimulator]"

    # Attribute Declarations
    distribution: CountCovariateDistribution
    generator: PopulationGenerator

    def __init__(self, distribution: CountCovariateDistribution,
                 generator: PopulationGenerator):
        """Create a simulator from a distribution and generator.

        Args:
            distribution: A covariate distribution with coefficients.
            generator: A population generator with a PopulationSpec.

        Raises:
            TypeError: If arguments are wrong types.
        """
        self._validate_distribution(distribution)
        self._validate_generator(generator)
        self.distribution = distribution
        self.generator = generator

    @abstractmethod
    def _validate_distribution(self, distribution) -> None:
        """Check that the distribution is the right type.

        Each subclass validates its specific distribution type.

        Raises:
            TypeError: If distribution is wrong type.
        """
        ...

    def _validate_generator(self, generator) -> None:
        """Check that the generator is a PopulationGenerator.

        Raises:
            TypeError: If not a PopulationGenerator.
        """
        if not isinstance(generator, PopulationGenerator):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"generator must be PopulationGenerator, "
                f"got {type(generator).__name__}"
            )

    def simulate(self, n: int, seed: int = None) -> pd.DataFrame:
        """Generate fake count data for n people.

        Steps:
            1. Generate fake people (covariates) from the population spec
            2. For each component in the distribution, build its design
               matrix and compute per-person values
            3. Draw counts based on the computed values
            4. Return covariates DataFrame with event_count column

        Args:
            n: Number of people to simulate.
            seed: Optional random seed for reproducibility.

        Returns:
            DataFrame with one row per person, containing all
            covariate columns plus an 'event_count' column.

        Raises:
            TypeError: If n is not an integer.
            ValueError: If n is not positive.
        """
        if not isinstance(n, int):
            raise TypeError(
                f"{self._ERROR_PREFIX} simulate: "
                f"n must be an integer, got {type(n).__name__}"
            )
        if n <= 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} simulate: "
                f"n must be positive, got {n}"
            )

        # Step 1: Generate fake population
        covariates_df = self.generator.generate(n, seed=seed)

        # Step 2: Compute per-person values for each component
        component_values = self._compute_all_component_values(covariates_df)

        # Step 3: Draw counts (subclass-specific)
        rng = np.random.default_rng(seed)
        counts = self._draw_counts(rng, component_values, n)

        # Step 4: Attach counts to covariates
        result = covariates_df.copy()
        result["event_count"] = counts

        return result

    def _compute_all_component_values(self, covariates_df: pd.DataFrame) -> dict:
        """Compute per-person values for each component.

        For each component in the distribution, builds the design
        matrix from the appropriate covariates and multiplies by
        coefficients.

        Args:
            covariates_df: DataFrame from the population generator.

        Returns:
            Dict mapping component name to array of per-person values.
            e.g. {"rate": array([2.1, 3.5, ...]),
                  "dispersion": array([1.2, 1.5, ...])}
        """
        pop_spec = self.generator.population_spec
        categorical_cols = pop_spec.categorical_columns()

        component_values = {}

        for comp_name, comp_coefficients in self.distribution.coefficients.items():
            # Figure out which covariates this component uses
            spec_covariates = self.distribution.spec.get_component_covariates(comp_name)

            # Split into continuous and categorical for this component
            comp_continuous = [c for c in spec_covariates if c not in categorical_cols]
            comp_categorical = [c for c in spec_covariates if c in categorical_cols]

            # Get interactions for this component (if any)
            comp_interactions = self._get_component_interactions(comp_name, spec_covariates)

            # Build design matrix for this component
            matrix, col_names = build_design_matrix_dataframe(
                covariates_df,
                continuous_cols=comp_continuous,
                categorical_cols=comp_categorical,
                interactions=comp_interactions,
                encoding="dummy",
                add_intercept_col=True,
            )

            # Build coefficient vector matching column order
            coeff_vector = np.array([
                comp_coefficients.get(col, 0.0) for col in col_names
            ])

            # Compute linear predictor: X @ beta
            linear_predictor = matrix @ coeff_vector

            # Apply link function (exp for rate/dispersion, logistic for zero-inflation/hurdle)
            component_values[comp_name] = self._apply_link(comp_name, linear_predictor)

        return component_values

    def _get_component_interactions(self, comp_name: str,
                                     spec_covariates: list) -> list:
        """Get interaction terms relevant to a component.

        Filters the spec's interactions to only those where both
        covariates are in this component.

        Args:
            comp_name: Component name.
            spec_covariates: Covariates in this component.

        Returns:
            List of (col1, col2) tuples.
        """
        all_interactions = self.distribution.spec.interactions if hasattr(
            self.distribution.spec, 'interactions') else []

        relevant = []
        cov_set = set(spec_covariates)
        for interaction in all_interactions:
            if interaction[0] in cov_set and interaction[1] in cov_set:
                relevant.append(interaction)
        return relevant

    def _apply_link(self, comp_name: str, linear_predictor: np.ndarray) -> np.ndarray:
        """Apply the appropriate link function for a component.

        Rate and dispersion components use exp (log link).
        Zero-inflation and hurdle components use logistic (logit link).

        Args:
            comp_name: Component name.
            linear_predictor: X @ beta values.

        Returns:
            Transformed values.
        """
        if comp_name in ("zero_inflation", "hurdle"):
            # Logistic: 1 / (1 + exp(-x))
            return 1 / (1 + np.exp(-linear_predictor))
        else:
            # Exp: rate and dispersion components
            return np.exp(linear_predictor)

    @abstractmethod
    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        """Draw counts based on computed component values.

        Each subclass implements the specific drawing process.

        Args:
            rng: Numpy random generator.
            component_values: Dict of component name to per-person values.
                Values are already transformed (exp or logistic applied).
            n: Number of people.

        Returns:
            Array of n non-negative integer counts.
        """
        ...

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"distribution={self.distribution.__class__.__name__}, "
            f"generator={self.generator})"
        )
