"""Hurdle count covariate distributions.

Hurdle covariate distributions have two-stage coefficient sets:
one for the hurdle (logistic model for crossing the threshold)
and one for the count (truncated count model given crossing).

HurdlePoissonGamma adds a dispersion component.
"""

from .count_covariate_distributions import CountCovariateDistribution


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonCovariateDistribution(CountCovariateDistribution):
    """Hurdle Poisson covariate distribution.

    Two components: hurdle and count.
    P(cross hurdle)_i = logit(intercept + h1*age_i + ...)
    count_i | crossed = truncated Poisson with
        rate_i = exp(intercept + b1*age_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_spec_hurdle import HurdlePoissonCovariateSpec
        if not isinstance(spec, HurdlePoissonCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be HurdlePoissonCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaCovariateDistribution(CountCovariateDistribution):
    """Hurdle Poisson-Gamma covariate distribution.

    Three components: hurdle, count, and dispersion.
    P(cross hurdle)_i = logit(intercept + h1*age_i + ...)
    count_i | crossed = truncated PoissonGamma with
        rate_i = exp(intercept + b1*age_i + ...)
        dispersion_i = exp(intercept + g1*age_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_spec_hurdle import HurdlePoissonGammaCovariateSpec
        if not isinstance(spec, HurdlePoissonGammaCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be HurdlePoissonGammaCovariateSpec, "
                f"got {type(spec).__name__}"
            )
