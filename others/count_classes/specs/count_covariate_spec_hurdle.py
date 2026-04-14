"""Hurdle count covariate specs.

Hurdle models have two stages: a hurdle component (logistic model
for whether any events occur) and a count component (truncated
count model for how many events given they occur). Each stage
can have different covariates.

HurdlePoissonGamma adds a dispersion component on top.
"""

from .count_covariate_specs import CountCovariateSpec, _validate_exact_components


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonCovariateSpec(CountCovariateSpec):
    """Spec for Hurdle Poisson regression.

    Two components: hurdle and count.
    P(cross hurdle) = logit(intercept + h1*age + ...)
    count | crossed = truncated Poisson with rate = exp(intercept + b1*age + ...)
    """

    _REQUIRED = {"hurdle", "count"}

    def __init__(self, hurdle_covariates: list, count_covariates: list):
        """Create a Hurdle Poisson covariate spec.

        Args:
            hurdle_covariates: Covariates for the hurdle (yes/no) component.
            count_covariates: Covariates for the count (how many) component.
        """
        super().__init__({
            "hurdle": hurdle_covariates,
            "count": count_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaCovariateSpec(CountCovariateSpec):
    """Spec for Hurdle Poisson-Gamma regression.

    Three components: hurdle, count, and dispersion.
    P(cross hurdle) = logit(intercept + h1*age + ...)
    count | crossed = truncated PoissonGamma
        rate = exp(intercept + b1*age + ...)
        dispersion = exp(intercept + g1*age + ...)
    """

    _REQUIRED = {"hurdle", "count", "dispersion"}

    def __init__(self, hurdle_covariates: list, count_covariates: list,
                 dispersion_covariates: list):
        """Create a Hurdle Poisson-Gamma covariate spec.

        Args:
            hurdle_covariates: Covariates for the hurdle component.
            count_covariates: Covariates for the count component.
            dispersion_covariates: Covariates for the dispersion component.
        """
        super().__init__({
            "hurdle": hurdle_covariates,
            "count": count_covariates,
            "dispersion": dispersion_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)
