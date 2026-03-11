"""Poisson Mixture count regression spec.

The mixture regression spec is more complex than the others because
the number of components (K) is variable. Each component has its
own rate covariates, and there's a separate weight component that
determines membership probabilities.
"""

from .count_regression_specs import CountRegressionSpec


class PoissonMixtureRegressionSpec(CountRegressionSpec):
    """Spec for Poisson Mixture regression.

    Variable number of rate components plus a weight component.
    Each group can have different covariates driving its rate.

    Components:
        rate_1, rate_2, ..., rate_K: covariates for each group's rate
        weights: covariates that predict group membership

    Attributes:
        k (int): Number of mixture components.
        components (dict): Component name to covariate list mapping.

    Example:
        >>> spec = PoissonMixtureRegressionSpec(
        ...     k=2,
        ...     rate_covariates_per_component={
        ...         1: ["age", "BMI"],
        ...         2: ["age", "BMI", "county"],
        ...     },
        ...     weight_covariates=["age", "previous_diagnosis"],
        ... )
    """

    _ERROR_PREFIX = "[PoissonMixtureRegressionSpec]"

    # Attribute Declarations
    k: int

    def __init__(self, k: int, rate_covariates_per_component: dict,
                 weight_covariates: list):
        """Create a Poisson Mixture regression spec.

        Args:
            k: Number of mixture components. Must be >= 2.
            rate_covariates_per_component: Dict mapping component number
                (1-indexed) to list of covariates for that component's rate.
                e.g. {1: ["age", "BMI"], 2: ["age", "BMI", "county"]}
            weight_covariates: Covariates for the mixing weight model.

        Raises:
            TypeError: If arguments are wrong types.
            ValueError: If k < 2, component numbers don't match k,
                or covariates are invalid.
        """
        self.k = k
        self._validate_k(k)
        self._validate_rate_covariates(k, rate_covariates_per_component)

        # Build components dict
        components = {}
        for j in range(1, k + 1):
            components[f"rate_{j}"] = rate_covariates_per_component[j]
        components["weights"] = weight_covariates

        super().__init__(components)

    def _validate_k(self, k) -> None:
        """Validate k is a positive integer >= 2."""
        if not isinstance(k, int):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"k must be an integer, got {type(k).__name__}"
            )
        if k < 2:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"k must be at least 2, got {k}"
            )

    def _validate_rate_covariates(self, k, rate_covariates_per_component) -> None:
        """Validate rate covariates dict matches k."""
        if not isinstance(rate_covariates_per_component, dict):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"rate_covariates_per_component must be a dict, "
                f"got {type(rate_covariates_per_component).__name__}"
            )

        expected_keys = set(range(1, k + 1))
        actual_keys = set(rate_covariates_per_component.keys())

        missing = expected_keys - actual_keys
        if missing:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Missing rate covariates for components: {missing}. "
                f"Expected keys 1 through {k}."
            )

        unexpected = actual_keys - expected_keys
        if unexpected:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Unexpected component keys: {unexpected}. "
                f"Expected keys 1 through {k}."
            )

    def _validate_required_components(self, components: dict) -> None:
        """Validate that rate_1 through rate_K and weights are present."""
        expected = set(f"rate_{j}" for j in range(1, self.k + 1))
        expected.add("weights")
        present = set(components.keys())

        missing = expected - present
        if missing:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Missing required components: {missing}"
            )

        unexpected = present - expected
        if unexpected:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Unexpected components: {unexpected}. "
                f"Expected: {expected}"
            )

    def required_components(self) -> list:
        components = [f"rate_{j}" for j in range(1, self.k + 1)]
        components.append("weights")
        return components

    def describe(self) -> list:
        """Describe this mixture regression spec."""
        lines = [f"PoissonMixtureRegressionSpec (K={self.k})"]
        for j in range(1, self.k + 1):
            covs = self.components[f"rate_{j}"]
            cov_str = ", ".join(covs) if covs else "(intercept only)"
            lines.append(f"  rate_{j}: {cov_str}")
        weight_covs = self.components["weights"]
        weight_str = ", ".join(weight_covs) if weight_covs else "(intercept only)"
        lines.append(f"  weights: {weight_str}")
        return lines

    def __repr__(self) -> str:
        return (
            f"PoissonMixtureRegressionSpec(K={self.k}, "
            f"{len(self.unique_covariates())} unique covariates)"
        )
