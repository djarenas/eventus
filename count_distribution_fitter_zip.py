"""Zero-inflated count distribution fitters.

Fitters for ZIP and ZIPG distributions. Both require numerical
optimization since there is no closed-form MLE for zero-inflated
models. The zero-inflation parameter pi is entangled with the
count distribution parameters.
"""

import numpy as np
from scipy.stats import poisson, nbinom
from scipy.optimize import minimize

from .count_distributions import (
    ZIPDistribution,
    ZIPGDistribution,
)
from .count_distribution_fitters import CountDistributionFitter


# =====================================================================
#  ZIP Fitter
# =====================================================================

class ZIPFitter(CountDistributionFitter):
    """Fits a Zero-Inflated Poisson distribution to count data.

    Uses method of moments for initialization, then MLE via
    numerical optimization.
    """

    def fit(self) -> ZIPDistribution:
        """Estimate pi and lambda via MLE.

        Initializes with method of moments estimates, then
        refines using L-BFGS-B optimization.

        Returns:
            ZIPDistribution with fitted pi and lambda.
        """
        counts = self.counts
        n = len(counts)
        n_zeros = (counts == 0).sum()
        mean = counts.mean()
        var = counts.var()

        # Initialize
        if var > mean and mean > 0:
            pi_init = 1 - (mean ** 2 / var)
            lambda_init = var / mean
        else:
            pi_init = n_zeros / n
            lambda_init = max(mean, 0.1)

        pi_init = np.clip(pi_init, 0.01, 0.99)

        # MLE
        def neg_log_lik(params):
            pi, lam = params
            zero_mask = counts == 0
            nonzero_mask = ~zero_mask

            ll = 0
            if zero_mask.any():
                p_zero = pi + (1 - pi) * np.exp(-lam)
                ll += np.sum(np.log(p_zero + 1e-10))
            if nonzero_mask.any():
                p_nonzero = (1 - pi) * poisson.pmf(counts[nonzero_mask], mu=lam)
                ll += np.sum(np.log(p_nonzero + 1e-10))

            return -ll

        result = minimize(
            neg_log_lik,
            x0=[pi_init, lambda_init],
            bounds=[(1e-4, 1 - 1e-4), (1e-4, None)],
            method="L-BFGS-B",
        )

        pi_hat, lambda_hat = result.x
        return ZIPDistribution({
            "pi": float(pi_hat),
            "lambda": float(lambda_hat),
        })


# =====================================================================
#  ZIPG Fitter
# =====================================================================

class ZIPGFitter(CountDistributionFitter):
    """Fits a Zero-Inflated Poisson-Gamma distribution to count data.

    Three-parameter optimization: pi (zero-inflation), alpha
    (Gamma shape), and beta (Gamma rate). Initializes from
    zero proportion and method of moments on non-zero data.
    """

    def fit(self) -> ZIPGDistribution:
        """Estimate pi, alpha, and beta via MLE.

        Returns:
            ZIPGDistribution with fitted pi, alpha, and beta.
        """
        counts = self.counts
        n = len(counts)
        n_zeros = (counts == 0).sum()

        # Initialize
        pi_init = np.clip(n_zeros / n, 0.01, 0.99)

        nonzero = counts[counts > 0]
        if len(nonzero) > 1 and nonzero.var() > nonzero.mean():
            nz_mean = nonzero.mean()
            nz_var = nonzero.var()
            beta_init = nz_mean / (nz_var - nz_mean)
            alpha_init = nz_mean * beta_init
        else:
            alpha_init = 1.0
            beta_init = 1.0

        # MLE
        def neg_log_lik(params):
            pi, alpha, beta = params
            r = alpha
            p = beta / (1 + beta)

            zero_mask = counts == 0
            nonzero_mask = ~zero_mask

            ll = 0
            if zero_mask.any():
                nb_zero = nbinom.pmf(0, n=r, p=p)
                p_zero = pi + (1 - pi) * nb_zero
                ll += np.sum(np.log(p_zero + 1e-10))
            if nonzero_mask.any():
                nb_vals = nbinom.pmf(counts[nonzero_mask], n=r, p=p)
                p_nonzero = (1 - pi) * nb_vals
                ll += np.sum(np.log(p_nonzero + 1e-10))

            return -ll

        result = minimize(
            neg_log_lik,
            x0=[pi_init, alpha_init, beta_init],
            bounds=[(1e-4, 1 - 1e-4), (1e-4, None), (1e-4, None)],
            method="L-BFGS-B",
        )

        pi_hat, alpha_hat, beta_hat = result.x
        return ZIPGDistribution({
            "pi": float(pi_hat),
            "alpha": float(alpha_hat),
            "beta": float(beta_hat),
        })
