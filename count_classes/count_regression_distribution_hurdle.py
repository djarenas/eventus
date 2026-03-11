"""Hurdle count regression distributions.

Hurdle regression distributions have two-stage coefficient sets:
one for the hurdle (logistic model for crossing the threshold)
and one for the count (truncated count model given crossing).

HurdlePoissonGamma adds a dispersion component.
"""

from .count_regression_distributions import CountRegressionDistribution


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonRegressionDistribution(CountRegressionDistribution):
    """Hurdle Poisson regression distribution.

    Two components: hurdle and count.
    P(cross hurdle)_i = logit(intercept + h1*age_i + ...)
    count_i | crossed = truncated Poisson with
        rate_i = exp(intercept + b1*age_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_regression_spec_hurdle import HurdlePoissonRegressionSpec
        if not isinstance(spec, HurdlePoissonRegressionSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be HurdlePoissonRegressionSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaRegressionDistribution(CountRegressionDistribution):
    """Hurdle Poisson-Gamma regression distribution.

    Three components: hurdle, count, and dispersion.
    P(cross hurdle)_i = logit(intercept + h1*age_i + ...)
    count_i | crossed = truncated PoissonGamma with
        rate_i = exp(intercept + b1*age_i + ...)
        dispersion_i = exp(intercept + g1*age_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_regression_spec_hurdle import HurdlePoissonGammaRegressionSpec
        if not isinstance(spec, HurdlePoissonGammaRegressionSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be HurdlePoissonGammaRegressionSpec, "
                f"got {type(spec).__name__}"
            )
