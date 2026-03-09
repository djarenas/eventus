"""Poisson Mixture distribution fitter.

Uses the Expectation-Maximization (EM) algorithm to fit a finite
mixture of Poisson distributions. The number of components K can
be specified or auto-selected using BIC.

The EM algorithm is the most complex fitting procedure in the
toolkit, so the core loop and supporting functions are defined
as private methods to keep them organized.
"""

import numpy as np
from scipy.stats import poisson

from .count_distributions import PoissonMixtureDistribution
from .count_distribution_fitters import CountDistributionFitter


class PoissonMixtureFitter(CountDistributionFitter):
    """Fits a Poisson Mixture distribution via EM algorithm.

    If k is specified, fits exactly K components. If k is None,
    tries K=1 through K=5 and selects the best K using BIC.

    Attributes:
        k (int | None): Number of components. None = auto-select.

    Example:
        >>> fitter = PoissonMixtureFitter.from_counts(counts, k=3)
        >>> dist = fitter.fit()

        >>> fitter = PoissonMixtureFitter.from_counts(counts)  # auto K
        >>> dist = fitter.fit()
    """

    _ERROR_PREFIX = "[PoissonMixtureFitter]"

    # Attribute Declarations
    k: int | None

    def __init__(self, counts: np.ndarray, k: int | None = None):
        """Internal constructor.

        Args:
            counts: Numpy array of counts.
            k: Number of components, or None for auto-selection.
        """
        super().__init__(counts)
        self.k = k

    @classmethod
    def from_events(cls, events, k: int | None = None) -> "PoissonMixtureFitter":
        """Create from an Events object.

        Args:
            events: A validated Events object.
            k: Number of components, or None for auto-selection.

        Returns:
            A fitter ready to fit.
        """
        from .events import Events

        if not isinstance(events, Events):
            raise TypeError(
                f"{cls._ERROR_PREFIX} from_events: "
                f"Expected Events, got {type(events).__name__}"
            )
        if len(events) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} from_events: "
                f"Events object contains no data"
            )

        counts = events.count_per_person().values
        return cls(counts, k=k)

    @classmethod
    def from_counts(cls, counts, k: int | None = None) -> "PoissonMixtureFitter":
        """Create from raw count data.

        Args:
            counts: Array-like of non-negative integer counts.
            k: Number of components, or None for auto-selection.

        Returns:
            A fitter ready to fit.
        """
        counts = cls._validate_and_convert_counts(counts)
        return cls(counts, k=k)

    def fit(self, max_iter: int = 200, tol: float = 1e-6) -> PoissonMixtureDistribution:
        """Fit the Poisson mixture via EM.

        If k is None, tries K=1 through K=5 and picks the best
        by BIC. Otherwise fits exactly K components.

        Args:
            max_iter: Maximum EM iterations.
            tol: Convergence tolerance on log-likelihood change.

        Returns:
            PoissonMixtureDistribution with fitted parameters.
        """
        counts = self.counts.astype(float)

        if self.k is None:
            best_k, weights, lambdas = self._auto_select_k(
                counts, max_iter, tol
            )
            self.k = best_k
        else:
            weights, lambdas, _, _ = self._run_em(
                counts, self.k, max_iter, tol
            )

        # Build params dict
        params = {"k": self.k}
        for j in range(self.k):
            params[f"w{j + 1}"] = float(weights[j])
            params[f"lambda{j + 1}"] = float(lambdas[j])

        return PoissonMixtureDistribution(params)

    def _auto_select_k(
        self, counts: np.ndarray, max_iter: int, tol: float
    ) -> tuple:
        """Try K=1 through K=5, pick best by BIC.

        Args:
            counts: Array of counts.
            max_iter: Max EM iterations per K.
            tol: Convergence tolerance.

        Returns:
            Tuple of (best_k, best_weights, best_lambdas).
        """
        n = len(counts)
        best_k = 1
        best_bic = np.inf
        best_weights = None
        best_lambdas = None

        for k in range(1, 6):
            weights, lambdas, log_lik, _ = self._run_em(
                counts, k, max_iter, tol
            )
            n_params = 2 * k - 1
            bic = n_params * np.log(n) - 2 * log_lik

            if bic < best_bic:
                best_bic = bic
                best_k = k
                best_weights = weights
                best_lambdas = lambdas

        return best_k, best_weights, best_lambdas

    def _run_em(
        self,
        counts: np.ndarray,
        k: int,
        max_iter: int,
        tol: float,
    ) -> tuple:
        """Run the EM algorithm for a given K.

        Args:
            counts: Array of counts.
            k: Number of components.
            max_iter: Maximum iterations.
            tol: Convergence tolerance.

        Returns:
            Tuple of (weights, lambdas, log_likelihood, converged).
        """
        n = len(counts)
        weights, lambdas = self._initialize_em(counts, k)

        log_lik_prev = -np.inf
        resp = np.zeros((n, k))
        converged = False
        log_lik = log_lik_prev

        for iteration in range(max_iter):

            # E-step: compute responsibilities
            for j in range(k):
                resp[:, j] = weights[j] * poisson.pmf(counts, mu=lambdas[j])

            row_sums = resp.sum(axis=1, keepdims=True)
            row_sums = np.clip(row_sums, 1e-10, None)
            resp = resp / row_sums

            # M-step: update parameters
            n_j = resp.sum(axis=0)
            for j in range(k):
                if n_j[j] > 1e-10:
                    weights[j] = n_j[j] / n
                    lambdas[j] = np.sum(resp[:, j] * counts) / n_j[j]
                    lambdas[j] = max(lambdas[j], 1e-4)

            weights = weights / weights.sum()

            # Check convergence
            log_lik = np.sum(np.log(row_sums.flatten()))
            if abs(log_lik - log_lik_prev) < tol:
                converged = True
                break
            log_lik_prev = log_lik

        # Sort by lambda for consistent ordering
        order = np.argsort(lambdas)
        lambdas = lambdas[order]
        weights = weights[order]

        return weights, lambdas, log_lik, converged

    @staticmethod
    def _initialize_em(counts: np.ndarray, k: int) -> tuple:
        """Initialize EM with quantile-spaced lambdas.

        Args:
            counts: Array of counts.
            k: Number of components.

        Returns:
            Tuple of (weights, lambdas).
        """
        n = len(counts)
        sorted_counts = np.sort(counts)

        quantile_indices = np.linspace(0, n - 1, k + 2)[1:-1].astype(int)
        lambdas = sorted_counts[quantile_indices].astype(float)
        lambdas = np.clip(lambdas, 0.1, None)

        for i in range(1, k):
            if lambdas[i] <= lambdas[i - 1]:
                lambdas[i] = lambdas[i - 1] + 1.0

        weights = np.ones(k) / k

        return weights, lambdas
