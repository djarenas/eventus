"""Count distribution simulators.

A simulator generates fake count data from a distribution. Each
simulator is paired with a specific distribution type and follows
that distribution's generative process faithfully.

A simulator takes a distribution in its constructor and provides
one method: simulate_counts(n).
"""

from abc import ABC, abstractmethod
import numpy as np
from scipy.stats import poisson, gamma, geom

from .count_distributions import (
    CountDistribution,
    PoissonDistribution,
    PoissonGammaDistribution,
    GeometricDistribution,
    ZIPDistribution,
    ZIPGDistribution,
    GeneralizedPoissonDistribution,
    PoissonMixtureDistribution,
    HurdlePoissonDistribution,
    HurdlePoissonGammaDistribution,
)


class CountDistributionSimulator(ABC):
    """Base class for all count distribution simulators.

    A simulator holds a distribution and generates fake count data
    from it. Each subclass follows its distribution's generative
    process faithfully.

    Attributes:
        distribution (CountDistribution): The distribution to
            simulate from.
    """

    # Attribute Declarations
    distribution: CountDistribution

    def __init__(self, distribution: CountDistribution):
        """Create a simulator for the given distribution.

        Args:
            distribution: A validated distribution instance.

        Raises:
            TypeError: If distribution is the wrong type for this simulator.
        """
        self._validate_distribution(distribution)
        self.distribution = distribution

    @abstractmethod
    def _validate_distribution(self, distribution) -> None:
        """Check that the distribution is the right type.

        Raises:
            TypeError: If distribution is wrong type.
        """
        ...

    @abstractmethod
    def simulate_counts(self, n: int) -> np.ndarray:
        """Generate n simulated counts.

        Args:
            n: Number of counts to generate. Must be positive.

        Returns:
            Array of n non-negative integer counts.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.distribution})"


# =====================================================================
#  Poisson
# =====================================================================

class PoissonSimulator(CountDistributionSimulator):
    """Generates counts from a Poisson distribution.

    All individuals share the same constant rate lambda.
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonDistribution):
            raise TypeError(
                f"PoissonSimulator requires PoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Generate n Poisson draws at rate lambda."""
        return poisson.rvs(mu=self.distribution.params["lambda"], size=n)


# =====================================================================
#  Poisson-Gamma
# =====================================================================

class PoissonGammaSimulator(CountDistributionSimulator):
    """Generates counts from a Poisson-Gamma distribution.

    Generative process:
        1. Each person draws a rate from Gamma(alpha, beta)
        2. Their count follows Poisson(rate)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonGammaDistribution):
            raise TypeError(
                f"PoissonGammaSimulator requires PoissonGammaDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Draw person-level rates from Gamma, then counts from Poisson."""
        rates = gamma.rvs(
            a=self.distribution.params["alpha"],
            scale=1 / self.distribution.params["beta"],
            size=n,
        )
        return np.random.poisson(lam=rates)


# =====================================================================
#  Geometric
# =====================================================================

class GeometricSimulator(CountDistributionSimulator):
    """Generates counts from a Geometric distribution.

    Generative process:
        1. Each person draws a rate from Exponential (max heterogeneity)
        2. Their count follows Poisson(rate)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeometricDistribution):
            raise TypeError(
                f"GeometricSimulator requires GeometricDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Draw rates from Exponential, then counts from Poisson."""
        p = self.distribution.params["p"]
        rates = np.random.exponential(scale=(1 - p) / p, size=n)
        return np.random.poisson(lam=rates)


# =====================================================================
#  ZIP
# =====================================================================

class ZIPSimulator(CountDistributionSimulator):
    """Generates counts from a Zero-Inflated Poisson distribution.

    Generative process:
        1. With probability pi, person is a structural zero
        2. Otherwise, count follows Poisson(lambda)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPDistribution):
            raise TypeError(
                f"ZIPSimulator requires ZIPDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Flip structural zero coin, then draw from Poisson."""
        pi = self.distribution.params["pi"]
        lam = self.distribution.params["lambda"]

        is_structural_zero = np.random.random(n) < pi
        counts = poisson.rvs(mu=lam, size=n)
        counts[is_structural_zero] = 0
        return counts


# =====================================================================
#  ZIPG
# =====================================================================

class ZIPGSimulator(CountDistributionSimulator):
    """Generates counts from a Zero-Inflated Poisson-Gamma distribution.

    Generative process:
        1. With probability pi, person is a structural zero
        2. Otherwise, draw rate from Gamma(alpha, beta)
        3. Count follows Poisson(rate)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPGDistribution):
            raise TypeError(
                f"ZIPGSimulator requires ZIPGDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Structural zero coin flip, Gamma rate draw, then Poisson."""
        pi = self.distribution.params["pi"]
        alpha = self.distribution.params["alpha"]
        beta = self.distribution.params["beta"]

        is_structural_zero = np.random.random(n) < pi
        rates = gamma.rvs(a=alpha, scale=1 / beta, size=n)
        counts = np.random.poisson(lam=rates)
        counts[is_structural_zero] = 0
        return counts


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonSimulator(CountDistributionSimulator):
    """Generates counts from a Generalized Poisson distribution.

    No clean generative process exists. Uses CDF inversion sampling.
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeneralizedPoissonDistribution):
            raise TypeError(
                f"GeneralizedPoissonSimulator requires GeneralizedPoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Generate counts via CDF inversion sampling."""
        from .helper_count_distribution_probability import compute_pmf

        k_max = 50
        k_range = np.arange(0, k_max + 1)
        pmf_vals = compute_pmf(self.distribution, k_range)
        cdf_vals = np.cumsum(pmf_vals)

        u = np.random.random(n)
        samples = np.searchsorted(cdf_vals, u)
        return np.clip(samples, 0, k_max)


# =====================================================================
#  Poisson Mixture
# =====================================================================

class PoissonMixtureSimulator(CountDistributionSimulator):
    """Generates counts from a Poisson Mixture distribution.

    Generative process:
        1. Assign person to group j with probability w_j
        2. Count follows Poisson(lambda_j)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonMixtureDistribution):
            raise TypeError(
                f"PoissonMixtureSimulator requires PoissonMixtureDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Assign to component, then draw from that component's Poisson."""
        k = self.distribution.params["k"]
        weights = np.array([self.distribution.params[f"w{j}"] for j in range(1, k + 1)])
        lambdas = np.array([self.distribution.params[f"lambda{j}"] for j in range(1, k + 1)])

        components = np.random.choice(k, size=n, p=weights)
        counts = np.zeros(n, dtype=int)
        for j in range(k):
            mask = components == j
            counts[mask] = poisson.rvs(mu=lambdas[j], size=mask.sum())
        return counts


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonSimulator(CountDistributionSimulator):
    """Generates counts from a Hurdle Poisson distribution.

    Generative process:
        1. With probability pi, person crosses the hurdle
        2. Count follows zero-truncated Poisson(lambda)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonDistribution):
            raise TypeError(
                f"HurdlePoissonSimulator requires HurdlePoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Hurdle coin flip, then rejection-sampled zero-truncated Poisson."""
        pi = self.distribution.params["pi"]
        lam = self.distribution.params["lambda"]

        crosses_hurdle = np.random.random(n) < pi
        counts = np.zeros(n, dtype=int)
        n_active = crosses_hurdle.sum()

        if n_active > 0:
            active_counts = np.zeros(n_active, dtype=int)
            remaining = np.arange(n_active)

            while len(remaining) > 0:
                draws = poisson.rvs(mu=lam, size=len(remaining))
                nonzero = draws > 0
                active_counts[remaining[nonzero]] = draws[nonzero]
                remaining = remaining[~nonzero]

            counts[crosses_hurdle] = active_counts

        return counts


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaSimulator(CountDistributionSimulator):
    """Generates counts from a Hurdle Poisson-Gamma distribution.

    Generative process:
        1. With probability pi, person crosses the hurdle
        2. Draw personal rate from Gamma(alpha, beta)
        3. Count follows zero-truncated Poisson(rate)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonGammaDistribution):
            raise TypeError(
                f"HurdlePoissonGammaSimulator requires HurdlePoissonGammaDistribution, "
                f"got {type(distribution).__name__}"
            )

    def simulate_counts(self, n: int) -> np.ndarray:
        """Hurdle, Gamma rate draw, then rejection-sampled zero-truncated Poisson."""
        pi = self.distribution.params["pi"]
        alpha = self.distribution.params["alpha"]
        beta = self.distribution.params["beta"]

        crosses_hurdle = np.random.random(n) < pi
        counts = np.zeros(n, dtype=int)
        n_active = crosses_hurdle.sum()

        if n_active > 0:
            rates = gamma.rvs(a=alpha, scale=1 / beta, size=n_active)
            active_counts = np.zeros(n_active, dtype=int)
            remaining = np.arange(n_active)

            while len(remaining) > 0:
                draws = np.random.poisson(lam=rates[remaining])
                nonzero = draws > 0
                active_counts[remaining[nonzero]] = draws[nonzero]
                remaining = remaining[~nonzero]

            counts[crosses_hurdle] = active_counts

        return counts
