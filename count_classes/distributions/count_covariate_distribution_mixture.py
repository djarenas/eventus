"""Poisson Mixture count covariate distribution.

The mixture covariate distribution has variable numbers of
rate components plus a weight component, mirroring the structure
of PoissonMixtureCovariateSpec.
"""

from .count_covariate_distributions import CountCovariateDistribution


class PoissonMixtureCovariateDistribution(CountCovariateDistribution):
    """Poisson Mixture covariate distribution.

    Variable number of rate components plus weights.
    Each group has its own rate coefficients:
        rate_j_i = exp(intercept + b1_j*age_i + ...)
    Group membership:
        P(group j)_i = softmax(intercept + w1*age_i + ...)

    Attributes:
        spec: PoissonMixtureCovariateSpec
        coefficients: dict with keys rate_1, rate_2, ..., weights
        k (int): Number of mixture components (from spec).
    """

    _ERROR_PREFIX = "[PoissonMixtureCovariateDistribution]"

    @property
    def k(self) -> int:
        """Number of mixture components."""
        return self.spec.k

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_spec_mixture import PoissonMixtureCovariateSpec
        if not isinstance(spec, PoissonMixtureCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be PoissonMixtureCovariateSpec, "
                f"got {type(spec).__name__}"
            )

    def describe(self) -> list:
        """Describe this mixture covariate distribution."""
        lines = [f"PoissonMixtureCovariateDistribution (K={self.k})"]
        for j in range(1, self.k + 1):
            comp_name = f"rate_{j}"
            comp_coeffs = self.coefficients[comp_name]
            lines.append(f"  {comp_name}:")
            if "intercept" in comp_coeffs:
                lines.append(f"    intercept: {comp_coeffs['intercept']:.4f}")
            for cov_name in sorted(comp_coeffs.keys()):
                if cov_name != "intercept":
                    lines.append(f"    {cov_name}: {comp_coeffs[cov_name]:.4f}")

        weight_coeffs = self.coefficients["weights"]
        lines.append(f"  weights:")
        if "intercept" in weight_coeffs:
            lines.append(f"    intercept: {weight_coeffs['intercept']:.4f}")
        for cov_name in sorted(weight_coeffs.keys()):
            if cov_name != "intercept":
                lines.append(f"    {cov_name}: {weight_coeffs[cov_name]:.4f}")

        return lines

    def __repr__(self) -> str:
        n_coeffs = sum(len(c) for c in self.coefficients.values())
        return (
            f"PoissonMixtureCovariateDistribution("
            f"K={self.k}, {n_coeffs} coefficients)"
        )
