"""Count distribution fitters — base class and simple fitters.

A fitter takes count data and estimates the parameters of a
distribution. It returns a distribution object with fitted
parameters. That is all it does — no metrics, no plots, no
comparison. Those are the jobs of other objects.

This file contains the abstract base class and the fitters
with simple closed-form or method-of-moments solutions:
Poisson, Poisson-Gamma, and Geometric.
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

from .count_distributions import (
    CountDistribution,
    PoissonDistribution,
    PoissonGammaDistribution,
    GeometricDistribution,
)


class CountDistributionFitter(ABC):
    """Base class for all count distribution fitters.

    A fitter holds count data and estimates distribution parameters
    from it. The result of fitting is a CountDistribution object.

    Attributes:
        counts (pd.Series): The count data to fit against.

    Example:
        >>> fitter = PoissonFitter.from_counts(counts)
        >>> distribution = fitter.fit()
        >>> print(distribution)
        PoissonDistribution(lambda=4.2000)
    """

    # Attribute Declarations
    counts: pd.Series

    def __init__(self, counts: pd.Series):
        """Internal constructor. Use from_events() or from_counts().

        Args:
            counts: Series of non-negative integer counts.
        """
        self.counts = counts

    @classmethod
    def from_events(cls, events) -> "CountDistributionFitter":
        """Create a fitter from an Events object.

        Extracts counts per person from the Events object using
        its semantics.

        Args:
            events: A validated Events object.

        Returns:
            A fitter ready to fit.

        Raises:
            TypeError: If events is not an Events object.
            ValueError: If events contains no data.
        """
        from .events import Events

        if not isinstance(events, Events):
            raise TypeError(f"Expected Events, got {type(events).__name__}")
        if len(events) == 0:
            raise ValueError("Events object contains no data")

        counts = events.count_per_person()
        return cls(counts)

    @classmethod
    def from_counts(cls, counts) -> "CountDistributionFitter":
        """Create a fitter from raw count data.

        Args:
            counts: Array-like of non-negative integer counts
                (np.ndarray, list, or pd.Series).

        Returns:
            A fitter ready to fit.

        Raises:
            TypeError: If counts is not array-like or not integer-valued.
            ValueError: If counts is empty or contains nulls/negatives.
        """
        counts = cls._validate_and_convert_counts(counts)
        return cls(counts)

    @staticmethod
    def _validate_and_convert_counts(counts) -> pd.Series:
        """Validate and convert count data to pd.Series.

        Args:
            counts: Array-like of counts.

        Returns:
            Validated pd.Series.

        Raises:
            TypeError: If not array-like or not integer-valued.
            ValueError: If empty, has nulls, or has negatives.
        """
        if not isinstance(counts, (np.ndarray, pd.Series, list)):
            raise TypeError(f"Expected array-like, got {type(counts).__name__}")

        if isinstance(counts, pd.Series):
            series = counts.copy()
        else:
            series = pd.Series(counts, name="event_count")

        if len(series) == 0:
            raise ValueError("Counts array is empty")
        if series.isna().any():
            raise ValueError(f"Counts contain {series.isna().sum()} null values")
        if (series < 0).any():
            raise ValueError("Counts cannot contain negative values")

        return series

    @abstractmethod
    def fit(self) -> CountDistribution:
        """Estimate distribution parameters from the count data.

        Returns:
            A CountDistribution with fitted parameters.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(n={len(self.counts)})"


# =====================================================================
#  Poisson Fitter
# =====================================================================

class PoissonFitter(CountDistributionFitter):
    """Fits a Poisson distribution to count data.

    MLE for Poisson is the sample mean. Closed-form, no
    optimization needed.
    """

    def fit(self) -> PoissonDistribution:
        """Estimate lambda as the sample mean.

        Returns:
            PoissonDistribution with fitted lambda.
        """
        lambda_hat = self.counts.mean()
        return PoissonDistribution({"lambda": float(lambda_hat)})


# =====================================================================
#  Poisson-Gamma Fitter
# =====================================================================

class PoissonGammaFitter(CountDistributionFitter):
    """Fits a Poisson-Gamma distribution to count data.

    Uses method of moments when variance > mean (closed-form).
    Falls back to MLE optimization when method of moments fails.
    """

    def fit(self) -> PoissonGammaDistribution:
        """Estimate alpha and beta from count data.

        Method of moments:
            beta = mean / (variance - mean)
            alpha = mean * beta

        Falls back to MLE if variance <= mean.

        Returns:
            PoissonGammaDistribution with fitted alpha and beta.
        """
        mean = self.counts.mean()
        var = self.counts.var()

        if var > mean and mean > 0:
            beta_hat = mean / (var - mean)
            alpha_hat = mean * beta_hat
        else:
            alpha_hat, beta_hat = self._fit_mle()

        return PoissonGammaDistribution({
            "alpha": float(alpha_hat),
            "beta": float(beta_hat),
        })

    def _fit_mle(self) -> tuple:
        """Fallback MLE fitting using numerical optimization.

        Returns:
            Tuple of (alpha_hat, beta_hat).
        """
        from scipy.optimize import minimize
        from scipy.stats import nbinom

        def neg_log_lik(params):
            alpha, beta = params
            r = alpha
            p = beta / (1 + beta)
            pmf_vals = nbinom.pmf(self.counts.values, n=r, p=p)
            return -np.sum(np.log(pmf_vals + 1e-10))

        result = minimize(
            neg_log_lik,
            x0=[1.0, 1.0],
            bounds=[(1e-4, None), (1e-4, None)],
            method="L-BFGS-B",
        )
        return result.x[0], result.x[1]


# =====================================================================
#  Geometric Fitter
# =====================================================================

class GeometricFitter(CountDistributionFitter):
    """Fits a Geometric distribution to count data.

    MLE for Geometric: p = 1 / (1 + mean). Closed-form.
    """

    def fit(self) -> GeometricDistribution:
        """Estimate p from the sample mean.

        Returns:
            GeometricDistribution with fitted p.
        """
        mean = self.counts.mean()
        p_hat = 1 / (1 + mean)
        return GeometricDistribution({"p": float(p_hat)})
