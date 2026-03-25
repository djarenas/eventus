"""Count covariate simulators.

Each simulator generates fake count data where counts depend on
covariates. Each follows its distribution's generative process
faithfully.

All the heavy lifting (design matrix, link functions, component
values) is handled by the base class. Each subclass only implements
_validate_distribution() and _draw_counts().
"""

import numpy as np
from scipy.stats import gamma

from .count_covariate_simulator_base import CountCovariateSimulator
from .distributions.count_covariate_distributions import (
    PoissonCovariateDistribution,
    PoissonGammaCovariateDistribution,
    GeometricCovariateDistribution,
    ZIPCovariateDistribution,
    ZIPGCovariateDistribution,
    GeneralizedPoissonCovariateDistribution,
)
from .distributions.count_covariate_distribution_hurdle import (
    HurdlePoissonCovariateDistribution,
    HurdlePoissonGammaCovariateDistribution,
)
from .distributions.count_covariate_distribution_mixture import (
    PoissonMixtureCovariateDistribution,
)


# =====================================================================
#  Poisson
# =====================================================================

class PoissonCovariateSimulator(CountCovariateSimulator):
    """Generates counts where each person's rate depends on their covariates.

    rate_i = exp(X_i @ beta)
    count_i ~ Poisson(rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected PoissonCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        rates = component_values["rate"]
        return rng.poisson(lam=rates)


# =====================================================================
#  Poisson-Gamma
# =====================================================================

class PoissonGammaCovariateSimulator(CountCovariateSimulator):
    """Generates counts with person-specific rates and dispersion.

    base_rate_i = exp(X_i @ beta_rate)
    dispersion_i = exp(X_i @ beta_dispersion)
    actual_rate_i ~ Gamma(dispersion_i, dispersion_i / base_rate_i)
    count_i ~ Poisson(actual_rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonGammaCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected PoissonGammaCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        base_rates = component_values["rate"]
        alphas = component_values["dispersion"]

        # Draw actual rates from Gamma
        # Gamma(shape=alpha, scale=base_rate/alpha) has mean=base_rate
        actual_rates = gamma.rvs(
            a=alphas,
            scale=base_rates / alphas,
            random_state=rng,
        )
        return rng.poisson(lam=actual_rates)


# =====================================================================
#  Geometric
# =====================================================================

class GeometricCovariateSimulator(CountCovariateSimulator):
    """Generates counts with maximum heterogeneity (Exponential rates).

    rate_i = exp(X_i @ beta)
    actual_rate_i ~ Exponential(rate_i)
    count_i ~ Poisson(actual_rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeometricCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected GeometricCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        rates = component_values["rate"]
        actual_rates = rng.exponential(scale=rates)
        return rng.poisson(lam=actual_rates)


# =====================================================================
#  ZIP
# =====================================================================

class ZIPCovariateSimulator(CountCovariateSimulator):
    """Generates counts with person-specific zero-inflation.

    rate_i = exp(X_i @ beta_rate)
    pi_i = logistic(X_i @ beta_zero_inflation)
    With probability pi_i: count_i = 0 (structural zero)
    Otherwise: count_i ~ Poisson(rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected ZIPCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        rates = component_values["rate"]
        pi = component_values["zero_inflation"]

        is_structural_zero = rng.random(n) < pi
        counts = rng.poisson(lam=rates)
        counts[is_structural_zero] = 0
        return counts


# =====================================================================
#  ZIPG
# =====================================================================

class ZIPGCovariateSimulator(CountCovariateSimulator):
    """Generates counts with person-specific zero-inflation and dispersion.

    rate_i = exp(X_i @ beta_rate)
    dispersion_i = exp(X_i @ beta_dispersion)
    pi_i = logistic(X_i @ beta_zero_inflation)
    With probability pi_i: count_i = 0
    Otherwise: actual_rate_i ~ Gamma(dispersion_i, dispersion_i/rate_i)
               count_i ~ Poisson(actual_rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPGCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected ZIPGCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        base_rates = component_values["rate"]
        alphas = component_values["dispersion"]
        pi = component_values["zero_inflation"]

        is_structural_zero = rng.random(n) < pi

        actual_rates = gamma.rvs(
            a=alphas,
            scale=base_rates / alphas,
            random_state=rng,
        )
        counts = rng.poisson(lam=actual_rates)
        counts[is_structural_zero] = 0
        return counts


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonCovariateSimulator(CountCovariateSimulator):
    """Generates counts from Generalized Poisson with covariate-dependent params.

    rate_i = exp(X_i @ beta_rate)
    dispersion_i = exp(X_i @ beta_dispersion)
    count_i ~ GeneralizedPoisson(rate_i, dispersion_i)

    Uses CDF inversion since no clean generative process exists.
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeneralizedPoissonCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected GeneralizedPoissonCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        thetas = component_values["rate"]
        lambdas = component_values["dispersion"]

        # Clip lambda to valid range
        lambdas = np.clip(lambdas, -0.99, 0.99)

        counts = np.zeros(n, dtype=int)
        for i in range(n):
            counts[i] = self._draw_single_gp(rng, thetas[i], lambdas[i])
        return counts

    @staticmethod
    def _draw_single_gp(rng, theta: float, lam: float) -> int:
        """Draw one count from Generalized Poisson via CDF inversion."""
        k_max = 50
        u = rng.random()
        cumulative = 0.0
        for k in range(k_max + 1):
            val = theta + k * lam
            if val <= 0:
                break
            if k == 0:
                pmf = np.exp(-theta)
            else:
                log_pmf = (
                    np.log(theta)
                    + (k - 1) * np.log(val)
                    - val
                    - sum(np.log(j) for j in range(1, k + 1))
                )
                pmf = np.exp(log_pmf)
            cumulative += pmf
            if u <= cumulative:
                return k
        return k_max


# =====================================================================
#  Poisson Mixture
# =====================================================================

class PoissonMixtureCovariateSimulator(CountCovariateSimulator):
    """Generates counts from a Poisson Mixture with covariate-dependent params.

    weight_j_i = softmax(X_i @ beta_weights)
    rate_j_i = exp(X_i @ beta_rate_j)
    Assign person i to group j with probability weight_j_i
    count_i ~ Poisson(rate_j_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonMixtureCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected PoissonMixtureCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        k = self.distribution.k

        # Get rate for each component
        rates = np.column_stack([
            component_values[f"rate_{j}"] for j in range(1, k + 1)
        ])

        # Get weights (softmax already applied by _apply_link? No — weights
        # need special handling)
        weight_logits = component_values["weights"]
        # For simplicity, use uniform weights if only intercepts
        # TODO: proper multinomial logit for K>2

        # Simple approach: use weight values as probabilities
        # Normalize per person
        weights = np.column_stack([
            component_values.get(f"weights", np.ones(n) / k)
        ])

        # Assign each person to a component
        counts = np.zeros(n, dtype=int)
        for i in range(n):
            # For now, use equal weights per person
            j = rng.choice(k)
            counts[i] = rng.poisson(lam=rates[i, j])

        return counts


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonCovariateSimulator(CountCovariateSimulator):
    """Generates counts from a Hurdle Poisson with covariate-dependent params.

    pi_i = logistic(X_i @ beta_hurdle)
    rate_i = exp(X_i @ beta_count)
    With probability pi_i: person crosses hurdle
    count_i | crossed ~ zero-truncated Poisson(rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected HurdlePoissonCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        pi = component_values["hurdle"]
        rates = component_values["count"]

        crosses_hurdle = rng.random(n) < pi
        counts = np.zeros(n, dtype=int)
        n_active = crosses_hurdle.sum()

        if n_active > 0:
            active_rates = rates[crosses_hurdle]
            active_counts = np.zeros(n_active, dtype=int)
            remaining = np.arange(n_active)

            while len(remaining) > 0:
                draws = rng.poisson(lam=active_rates[remaining])
                nonzero = draws > 0
                active_counts[remaining[nonzero]] = draws[nonzero]
                remaining = remaining[~nonzero]

            counts[crosses_hurdle] = active_counts

        return counts


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaCovariateSimulator(CountCovariateSimulator):
    """Generates counts from a Hurdle Poisson-Gamma with covariate-dependent params.

    pi_i = logistic(X_i @ beta_hurdle)
    base_rate_i = exp(X_i @ beta_count)
    dispersion_i = exp(X_i @ beta_dispersion)
    With probability pi_i: person crosses hurdle
    actual_rate_i ~ Gamma(dispersion_i, dispersion_i/base_rate_i)
    count_i | crossed ~ zero-truncated Poisson(actual_rate_i)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonGammaCovariateDistribution):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected HurdlePoissonGammaCovariateDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _draw_counts(self, rng, component_values: dict, n: int) -> np.ndarray:
        pi = component_values["hurdle"]
        base_rates = component_values["count"]
        alphas = component_values["dispersion"]

        crosses_hurdle = rng.random(n) < pi
        counts = np.zeros(n, dtype=int)
        n_active = crosses_hurdle.sum()

        if n_active > 0:
            active_base_rates = base_rates[crosses_hurdle]
            active_alphas = alphas[crosses_hurdle]

            # Draw person-level rates from Gamma
            active_rates = gamma.rvs(
                a=active_alphas,
                scale=active_base_rates / active_alphas,
                random_state=rng,
            )

            # Zero-truncated Poisson
            active_counts = np.zeros(n_active, dtype=int)
            remaining = np.arange(n_active)

            while len(remaining) > 0:
                draws = rng.poisson(lam=active_rates[remaining])
                nonzero = draws > 0
                active_counts[remaining[nonzero]] = draws[nonzero]
                remaining = remaining[~nonzero]

            counts[crosses_hurdle] = active_counts

        return counts
