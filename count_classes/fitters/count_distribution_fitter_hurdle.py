"""Hurdle count distribution fitters.

Fitters for Hurdle Poisson and Hurdle Poisson-Gamma distributions.
Both use a two-stage fitting approach:
    Stage 1: Estimate hurdle probability pi from the proportion
             of non-zero observations (closed-form).
    Stage 2: Estimate count distribution parameters from non-zero
             observations only (zero-truncated MLE).
"""

import numpy as np
from scipy.stats import poisson, nbinom
from scipy.optimize import minimize

from .count_distributions import (
    HurdlePoissonDistribution,
    HurdlePoissonGammaDistribution,
)
from .count_distribution_fitters import CountDistributionFitter


# =====================================================================
#  Hurdle Poisson Fitter
# =====================================================================

class HurdlePoissonFitter(CountDistributionFitter):
    """Fits a Hurdle Poisson distribution to count data.

    Stage 1: pi = proportion of non-zero observations.
    Stage 2: lambda estimated via MLE on the zero-truncated
    Poisson, using only non-zero observations.
    """

    def fit(self) -> HurdlePoissonDistribution:
        """Estimate pi and lambda in two stages.

        Returns:
            HurdlePoissonDistribution with fitted pi and lambda.
        """
        counts = self.counts
        n = len(counts)
        nonzero = counts[counts > 0]
        n_nonzero = len(nonzero)

        # Stage 1: hurdle probability
        pi_hat = n_nonzero / n

        # Stage 2: zero-truncated Poisson MLE
        def neg_log_lik_truncated(lam):
            lam = lam[0]
            if lam <= 0:
                return 1e10
            log_norm = np.log(1 - np.exp(-lam))
            ll = np.sum(poisson.logpmf(nonzero, mu=lam)) - n_nonzero * log_norm
            return -ll

        lambda_init = nonzero.mean()

        result = minimize(
            neg_log_lik_truncated,
            x0=[lambda_init],
            bounds=[(1e-4, None)],
            method="L-BFGS-B",
        )

        lambda_hat = result.x[0]
        return HurdlePoissonDistribution({
            "pi": float(pi_hat),
            "lambda": float(lambda_hat),
        })


# =====================================================================
#  Hurdle Poisson-Gamma Fitter
# =====================================================================

class HurdlePoissonGammaFitter(CountDistributionFitter):
    """Fits a Hurdle Poisson-Gamma distribution to count data.

    Stage 1: pi = proportion of non-zero observations.
    Stage 2: alpha and beta estimated via MLE on the zero-truncated
    Negative Binomial, using only non-zero observations.
    """

    def fit(self) -> HurdlePoissonGammaDistribution:
        """Estimate pi, alpha, and beta in two stages.

        Returns:
            HurdlePoissonGammaDistribution with fitted pi, alpha, and beta.
        """
        counts = self.counts
        n = len(counts)
        nonzero = counts[counts > 0]
        n_nonzero = len(nonzero)

        # Stage 1: hurdle probability
        pi_hat = n_nonzero / n

        # Stage 2: zero-truncated NegBin MLE
        nz_mean = nonzero.mean()
        nz_var = nonzero.var()

        if nz_var > nz_mean and nz_mean > 0:
            beta_init = nz_mean / (nz_var - nz_mean)
            alpha_init = nz_mean * beta_init
        else:
            alpha_init = 1.0
            beta_init = 1.0

        def neg_log_lik_truncated(params):
            alpha, beta = params
            if alpha <= 0 or beta <= 0:
                return 1e10
            r = alpha
            p = beta / (1 + beta)

            nb_zero = nbinom.pmf(0, n=r, p=p)
            log_norm = np.log(1 - nb_zero)

            if log_norm == 0 or np.isnan(log_norm):
                return 1e10

            ll = np.sum(nbinom.logpmf(nonzero, n=r, p=p)) - n_nonzero * log_norm
            return -ll

        result = minimize(
            neg_log_lik_truncated,
            x0=[alpha_init, beta_init],
            bounds=[(1e-4, None), (1e-4, None)],
            method="L-BFGS-B",
        )

        alpha_hat, beta_hat = result.x
        return HurdlePoissonGammaDistribution({
            "pi": float(pi_hat),
            "alpha": float(alpha_hat),
            "beta": float(beta_hat),
        })
