"""Count distribution computers.

A computer calculates probability-related quantities from a
distribution. Each computer is paired with a specific distribution
type and knows how to evaluate that distribution's PMF, PPF,
expected value, variance, and survival function.

A computer takes a distribution in its constructor and provides
methods to compute quantities from it.
"""

from abc import ABC, abstractmethod
import numpy as np
from scipy.stats import poisson, nbinom, geom

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


class CountDistributionComputer(ABC):
    """Base class for all count distribution computers.

    A computer holds a distribution and computes probability-related
    quantities from it. Each subclass knows the specific math for
    its distribution type.

    Attributes:
        distribution (CountDistribution): The distribution to
            compute from.
    """

    # Attribute Declarations
    distribution: CountDistribution

    def __init__(self, distribution: CountDistribution):
        """Create a computer for the given distribution.

        Args:
            distribution: A validated distribution instance.

        Raises:
            TypeError: If distribution is the wrong type for this computer.
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
    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        """Compute P(X = k) for each value in k.

        Args:
            k: Array of non-negative integer count values.

        Returns:
            Array of probabilities, same shape as k.
        """
        ...

    @abstractmethod
    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        """Compute the count value at each probability threshold.

        Args:
            q: Array of probabilities in (0, 1).

        Returns:
            Array of count values, same shape as q.
        """
        ...

    # ---- Concrete methods: same logic for all distributions ----

    def compute_probability_of(self, k: int) -> float:
        """Compute P(X = k) for a single count value.

        Args:
            k: A single non-negative integer.

        Returns:
            The probability of observing exactly k events.
        """
        return float(self.compute_pmf(np.array([k]))[0])

    def compute_survival(self, k: int) -> float:
        """Compute P(X >= k).

        Args:
            k: Count threshold.

        Returns:
            The probability of observing k or more events.
        """
        if k <= 0:
            return 1.0
        k_range = np.arange(0, k)
        return float(1.0 - np.sum(self.compute_pmf(k_range)))

    def compute_expected_value(self) -> float:
        """Compute the theoretical mean E[X].

        Returns:
            The expected value of the distribution.
        """
        k_range = np.arange(0, 101)
        pmf_vals = self.compute_pmf(k_range)
        return float(np.sum(k_range * pmf_vals))

    def compute_variance(self) -> float:
        """Compute the theoretical variance Var(X).

        Returns:
            The variance of the distribution.
        """
        k_range = np.arange(0, 101)
        pmf_vals = self.compute_pmf(k_range)
        mean = float(np.sum(k_range * pmf_vals))
        e_x2 = float(np.sum(k_range ** 2 * pmf_vals))
        return e_x2 - mean ** 2

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.distribution})"


# ---- Helper for numerical PPF ----

def _numerical_ppf(pmf_func, q: np.ndarray, k_max: int = 100) -> np.ndarray:
    """Compute PPF by building CDF from PMF and inverting.

    Args:
        pmf_func: A callable that takes k array and returns probabilities.
        q: Array of probabilities in (0, 1).
        k_max: Upper bound for CDF computation.

    Returns:
        Array of count values.
    """
    k_range = np.arange(0, k_max + 1)
    pmf_vals = pmf_func(k_range)
    cdf_vals = np.cumsum(pmf_vals)

    result = np.zeros_like(q, dtype=float)
    for i, qi in enumerate(q):
        idx = np.searchsorted(cdf_vals, qi)
        result[i] = min(idx, k_max)

    return result


# =====================================================================
#  Poisson
# =====================================================================

class PoissonComputer(CountDistributionComputer):
    """Computes probabilities for a Poisson distribution."""

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonDistribution):
            raise TypeError(
                f"PoissonComputer requires PoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        return poisson.pmf(k, mu=self.distribution.params["lambda"])

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return poisson.ppf(q, mu=self.distribution.params["lambda"])


# =====================================================================
#  Poisson-Gamma
# =====================================================================

class PoissonGammaComputer(CountDistributionComputer):
    """Computes probabilities for a Poisson-Gamma distribution.

    Internally converts alpha/beta to scipy's Negative Binomial
    parameterization (r, p).
    """

    def _to_scipy_params(self) -> tuple:
        r = self.distribution.params["alpha"]
        p = self.distribution.params["beta"] / (1 + self.distribution.params["beta"])
        return r, p

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonGammaDistribution):
            raise TypeError(
                f"PoissonGammaComputer requires PoissonGammaDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        r, p = self._to_scipy_params()
        return nbinom.pmf(k, n=r, p=p)

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        r, p = self._to_scipy_params()
        return nbinom.ppf(q, n=r, p=p)


# =====================================================================
#  Geometric
# =====================================================================

class GeometricComputer(CountDistributionComputer):
    """Computes probabilities for a Geometric distribution.

    Scipy's geom is defined on {1, 2, 3, ...} so we shift by 1
    to work on {0, 1, 2, ...}.
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeometricDistribution):
            raise TypeError(
                f"GeometricComputer requires GeometricDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        return geom.pmf(k + 1, p=self.distribution.params["p"])

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return geom.ppf(q, p=self.distribution.params["p"]) - 1


# =====================================================================
#  ZIP
# =====================================================================

class ZIPComputer(CountDistributionComputer):
    """Computes probabilities for a Zero-Inflated Poisson distribution.

    P(X = 0) = pi + (1 - pi) * exp(-lambda)
    P(X = k) = (1 - pi) * Poisson(k, lambda)   for k >= 1
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPDistribution):
            raise TypeError(
                f"ZIPComputer requires ZIPDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        pi = self.distribution.params["pi"]
        lam = self.distribution.params["lambda"]
        pmf = (1 - pi) * poisson.pmf(k, mu=lam)
        zero_mask = k == 0
        pmf[zero_mask] = pi + (1 - pi) * np.exp(-lam)
        return pmf

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)


# =====================================================================
#  ZIPG
# =====================================================================

class ZIPGComputer(CountDistributionComputer):
    """Computes probabilities for a Zero-Inflated Poisson-Gamma distribution.

    P(X = 0) = pi + (1 - pi) * NB(0; alpha, beta)
    P(X = k) = (1 - pi) * NB(k; alpha, beta)   for k >= 1
    """

    def _to_scipy_params(self) -> tuple:
        r = self.distribution.params["alpha"]
        p = self.distribution.params["beta"] / (1 + self.distribution.params["beta"])
        return r, p

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, ZIPGDistribution):
            raise TypeError(
                f"ZIPGComputer requires ZIPGDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        pi = self.distribution.params["pi"]
        r, p = self._to_scipy_params()
        pmf = (1 - pi) * nbinom.pmf(k, n=r, p=p)
        zero_mask = k == 0
        pmf[zero_mask] = pi + (1 - pi) * nbinom.pmf(0, n=r, p=p)
        return pmf

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonComputer(CountDistributionComputer):
    """Computes probabilities for a Generalized Poisson distribution.

    No scipy equivalent exists. PMF is computed manually.
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, GeneralizedPoissonDistribution):
            raise TypeError(
                f"GeneralizedPoissonComputer requires GeneralizedPoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        theta = self.distribution.params["theta"]
        lam = self.distribution.params["lambda"]
        return np.array([self._gp_pmf_single(int(ki), theta, lam) for ki in k])

    @staticmethod
    def _gp_pmf_single(k: int, theta: float, lam: float) -> float:
        """Compute GP PMF for a single k value."""
        val = theta + k * lam
        if val <= 0:
            return 0.0
        if k == 0:
            return np.exp(-theta)
        log_pmf = (
            np.log(theta)
            + (k - 1) * np.log(val)
            - val
            - sum(np.log(i) for i in range(1, k + 1))
        )
        return np.exp(log_pmf)

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)


# =====================================================================
#  Poisson Mixture
# =====================================================================

class PoissonMixtureComputer(CountDistributionComputer):
    """Computes probabilities for a Poisson Mixture distribution.

    P(X = k) = sum_j  w_j * Poisson(k; lambda_j)
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, PoissonMixtureDistribution):
            raise TypeError(
                f"PoissonMixtureComputer requires PoissonMixtureDistribution, "
                f"got {type(distribution).__name__}"
            )

    def _get_weights_and_lambdas(self) -> tuple:
        n_k = self.distribution.params["k"]
        weights = np.array([self.distribution.params[f"w{j}"] for j in range(1, n_k + 1)])
        lambdas = np.array([self.distribution.params[f"lambda{j}"] for j in range(1, n_k + 1)])
        return weights, lambdas

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        weights, lambdas = self._get_weights_and_lambdas()
        pmf = np.zeros_like(k, dtype=float)
        for j in range(len(weights)):
            pmf += weights[j] * poisson.pmf(k, mu=lambdas[j])
        return pmf

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonComputer(CountDistributionComputer):
    """Computes probabilities for a Hurdle Poisson distribution.

    P(X = 0) = 1 - pi
    P(X = k) = pi * Poisson(k, lambda) / (1 - exp(-lambda))   for k >= 1
    """

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonDistribution):
            raise TypeError(
                f"HurdlePoissonComputer requires HurdlePoissonDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        pi = self.distribution.params["pi"]
        lam = self.distribution.params["lambda"]
        truncation_norm = 1 - np.exp(-lam)
        pmf = pi * poisson.pmf(k, mu=lam) / truncation_norm
        zero_mask = k == 0
        pmf[zero_mask] = 1 - pi
        return pmf

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaComputer(CountDistributionComputer):
    """Computes probabilities for a Hurdle Poisson-Gamma distribution.

    P(X = 0) = 1 - pi
    P(X = k) = pi * NB(k; alpha, beta) / (1 - NB(0; alpha, beta))   for k >= 1
    """

    def _to_scipy_params(self) -> tuple:
        r = self.distribution.params["alpha"]
        p = self.distribution.params["beta"] / (1 + self.distribution.params["beta"])
        return r, p

    def _validate_distribution(self, distribution) -> None:
        if not isinstance(distribution, HurdlePoissonGammaDistribution):
            raise TypeError(
                f"HurdlePoissonGammaComputer requires HurdlePoissonGammaDistribution, "
                f"got {type(distribution).__name__}"
            )

    def compute_pmf(self, k: np.ndarray) -> np.ndarray:
        pi = self.distribution.params["pi"]
        r, p = self._to_scipy_params()
        nb_zero = nbinom.pmf(0, n=r, p=p)
        truncation_norm = 1 - nb_zero
        pmf = pi * nbinom.pmf(k, n=r, p=p) / truncation_norm
        zero_mask = k == 0
        pmf[zero_mask] = 1 - pi
        return pmf

    def compute_ppf(self, q: np.ndarray) -> np.ndarray:
        return _numerical_ppf(self.compute_pmf, q)
