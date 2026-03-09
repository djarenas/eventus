"""Generalized Poisson distribution fitter.

The Generalized Poisson has no closed-form MLE. Uses method of
moments for initialization, then numerical optimization.
"""

import numpy as np
from scipy.optimize import minimize

from .count_distributions import GeneralizedPoissonDistribution
from .count_distribution_fitters import CountDistributionFitter


class GeneralizedPoissonFitter(CountDistributionFitter):
    """Fits a Generalized Poisson distribution to count data.

    Method of moments initialization:
        lambda = 1 - sqrt(mean / variance)
        theta = mean * (1 - lambda)

    Then refined via MLE optimization.
    """

    def fit(self) -> GeneralizedPoissonDistribution:
        """Estimate theta and lambda via MLE.

        Returns:
            GeneralizedPoissonDistribution with fitted theta and lambda.
        """
        counts = self.counts.values
        mean = counts.mean()
        var = counts.var()

        # Method of moments initialization
        if var > 0:
            lambda_init = np.clip(1 - np.sqrt(mean / var), -0.9, 0.9)
            theta_init = max(mean * (1 - lambda_init), 0.1)
        else:
            lambda_init = 0.0
            theta_init = max(mean, 0.1)

        # MLE
        def neg_log_lik(params):
            theta, lam = params
            ll = 0
            for k in counts:
                val = theta + k * lam
                if val <= 0:
                    return 1e10
                log_pmf = (
                    np.log(theta)
                    + (k - 1) * np.log(val)
                    - val
                    - sum(np.log(i) for i in range(1, k + 1))
                )
                ll += log_pmf
            return -ll

        result = minimize(
            neg_log_lik,
            x0=[theta_init, lambda_init],
            bounds=[(1e-4, None), (-0.99, 0.99)],
            method="L-BFGS-B",
        )

        theta_hat, lambda_hat = result.x
        return GeneralizedPoissonDistribution({
            "theta": float(theta_hat),
            "lambda": float(lambda_hat),
        })
