"""Count covariate distributions — base class and simple distributions.

A covariate distribution is the result of fitting a count regression
model to data. It holds the spec (model design) and the fitted
coefficients. It is a concept — "I am a PoissonGamma regression
where rate depends on age by 0.03 and BMI by 0.05."

A covariate distribution does not hold data, does not compute
predictions, and does not plot. Those are the jobs of other objects.
"""

from abc import ABC, abstractmethod
import pandas as pd

from .count_covariate_specs import CountCovariateSpec


class CountCovariateDistribution(ABC):
    """Base class for all count covariate distributions.

    A covariate distribution holds a spec (the model design) and
    the fitted coefficients for each component. It can describe
    itself and validate that its coefficients match its spec.

    Attributes:
        spec (CountCovariateSpec): The model design blueprint.
        coefficients (dict): Maps component name to dict of
            covariate name → coefficient value.
            e.g. {"rate": {"intercept": 1.2, "age": 0.03}, ...}

    Example:
        >>> dist.describe()
        ['PoissonGammaCovariateDistribution',
         '  Rate:',
         '    intercept: 1.2000',
         '    age: 0.0300',
         '  Dispersion:',
         '    intercept: 0.8000']
    """

    _ERROR_PREFIX = "[CountCovariateDistribution]"

    # Attribute Declarations
    spec: CountCovariateSpec
    coefficients: dict

    def __init__(self, spec: CountCovariateSpec, coefficients: dict):
        """Create a covariate distribution from a spec and coefficients.

        Validates that the spec is the right type for this distribution,
        that coefficients match the spec's components, and that all
        values are numeric.

        Args:
            spec: The model design blueprint.
            coefficients: Dict mapping component names to coefficient dicts.

        Raises:
            TypeError: If spec or coefficients are wrong types.
            ValueError: If coefficients don't match spec components.
        """
        self._validate_spec_type(spec)
        self._validate_coefficients_structure(spec, coefficients)
        self._validate_coefficients_values(coefficients)
        self._validate_intercepts(coefficients)
        self.spec = spec
        self.coefficients = coefficients

    @abstractmethod
    def _validate_spec_type(self, spec) -> None:
        """Check that the spec is the right type for this distribution.

        Raises:
            TypeError: If spec is wrong type.
        """
        ...

    def _validate_coefficients_structure(self, spec, coefficients) -> None:
        """Check that coefficient keys match spec components.

        Raises:
            TypeError: If coefficients is not a dict of dicts.
            ValueError: If component names don't match.
        """
        if not isinstance(coefficients, dict):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"coefficients must be a dict, got {type(coefficients).__name__}"
            )

        spec_components = set(spec.component_names())
        coeff_components = set(coefficients.keys())

        missing = spec_components - coeff_components
        if missing:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Missing coefficients for components: {missing}"
            )

        unexpected = coeff_components - spec_components
        if unexpected:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Unexpected coefficient components: {unexpected}. "
                f"Spec components: {spec_components}"
            )

        for comp_name, comp_coeffs in coefficients.items():
            if not isinstance(comp_coeffs, dict):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Coefficients for '{comp_name}' must be a dict, "
                    f"got {type(comp_coeffs).__name__}"
                )

    def _validate_coefficients_values(self, coefficients) -> None:
        """Check that all coefficient values are numeric.

        Raises:
            TypeError: If any coefficient value is not numeric.
        """
        for comp_name, comp_coeffs in coefficients.items():
            for cov_name, value in comp_coeffs.items():
                if not isinstance(value, (int, float)):
                    raise TypeError(
                        f"{self._ERROR_PREFIX} __init__: "
                        f"Coefficient '{cov_name}' in '{comp_name}' "
                        f"must be numeric, got {type(value).__name__}"
                    )

    def _validate_intercepts(self, coefficients) -> None:
        """Check that every component has an intercept.

        Raises:
            ValueError: If any component is missing an intercept.
        """
        for comp_name, comp_coeffs in coefficients.items():
            if "intercept" not in comp_coeffs:
                raise ValueError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Component '{comp_name}' is missing an 'intercept' coefficient"
                )

    # ---- Accessors ----

    def get_component_coefficients(self, component_name: str) -> dict:
        """Get coefficients for a specific component.

        Args:
            component_name: Name of the component.

        Returns:
            Dict of covariate name → coefficient value.

        Raises:
            KeyError: If component not found.
        """
        if component_name not in self.coefficients:
            raise KeyError(
                f"{self._ERROR_PREFIX} get_component_coefficients: "
                f"'{component_name}' not found. "
                f"Available: {list(self.coefficients.keys())}"
            )
        return self.coefficients[component_name]

    def coefficient_table(self) -> pd.DataFrame:
        """Produce a clean table of all coefficients.

        Returns:
            DataFrame with columns: component, covariate, coefficient.
            Sorted by component then covariate.
        """
        rows = []
        for comp_name, comp_coeffs in self.coefficients.items():
            for cov_name, value in comp_coeffs.items():
                rows.append({
                    "component": comp_name,
                    "covariate": cov_name,
                    "coefficient": value,
                })
        return pd.DataFrame(rows).sort_values(
            ["component", "covariate"]
        ).reset_index(drop=True)

    def describe(self) -> list:
        """Describe this distribution in plain language.

        Returns:
            List of descriptive strings showing spec structure
            with fitted coefficient values.
        """
        lines = [self.__class__.__name__]
        for comp_name, comp_coeffs in self.coefficients.items():
            lines.append(f"  {comp_name}:")
            # Intercept first, then alphabetical
            if "intercept" in comp_coeffs:
                lines.append(f"    intercept: {comp_coeffs['intercept']:.4f}")
            for cov_name in sorted(comp_coeffs.keys()):
                if cov_name != "intercept":
                    lines.append(f"    {cov_name}: {comp_coeffs[cov_name]:.4f}")
        return lines

    def to_dict(self) -> dict:
        """Export as a plain dictionary.

        Returns:
            Dict with distribution type, spec, and coefficients.
        """
        return {
            "distribution": self.__class__.__name__,
            "spec": self.spec.to_dict(),
            "coefficients": {
                comp: dict(coeffs)
                for comp, coeffs in self.coefficients.items()
            },
        }

    def __repr__(self) -> str:
        n_coeffs = sum(len(c) for c in self.coefficients.values())
        n_components = len(self.coefficients)
        return (
            f"{self.__class__.__name__}("
            f"{n_components} components, "
            f"{n_coeffs} coefficients)"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, CountCovariateDistribution):
            return False
        return (self.__class__ == other.__class__
                and self.spec == other.spec
                and self.coefficients == other.coefficients)


# =====================================================================
#  Poisson
# =====================================================================

class PoissonCovariateDistribution(CountCovariateDistribution):
    """Poisson covariate distribution.

    One component: rate.
    rate_i = exp(intercept + b1*age_i + b2*BMI_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import PoissonCovariateSpec
        if not isinstance(spec, PoissonCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be PoissonCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  Poisson-Gamma
# =====================================================================

class PoissonGammaCovariateDistribution(CountCovariateDistribution):
    """Poisson-Gamma covariate distribution.

    Two components: rate and dispersion.
    rate_i = exp(intercept + b1*age_i + ...)
    dispersion_i = exp(intercept + g1*age_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import PoissonGammaCovariateSpec
        if not isinstance(spec, PoissonGammaCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be PoissonGammaCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  Geometric
# =====================================================================

class GeometricCovariateDistribution(CountCovariateDistribution):
    """Geometric covariate distribution.

    One component: rate.
    Special case of PoissonGamma with fixed maximum dispersion.
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import GeometricCovariateSpec
        if not isinstance(spec, GeometricCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be GeometricCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  ZIP
# =====================================================================

class ZIPCovariateDistribution(CountCovariateDistribution):
    """Zero-Inflated Poisson covariate distribution.

    Two components: rate and zero_inflation.
    rate_i = exp(intercept + b1*age_i + ...)
    P(structural zero)_i = logit(intercept + z1*prev_dx_i + ...)
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import ZIPCovariateSpec
        if not isinstance(spec, ZIPCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be ZIPCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  ZIPG
# =====================================================================

class ZIPGCovariateDistribution(CountCovariateDistribution):
    """Zero-Inflated Poisson-Gamma covariate distribution.

    Three components: rate, dispersion, and zero_inflation.
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import ZIPGCovariateSpec
        if not isinstance(spec, ZIPGCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be ZIPGCovariateSpec, "
                f"got {type(spec).__name__}"
            )


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonCovariateDistribution(CountCovariateDistribution):
    """Generalized Poisson covariate distribution.

    Two components: rate and dispersion.
    """

    def _validate_spec_type(self, spec) -> None:
        from .count_covariate_specs import GeneralizedPoissonCovariateSpec
        if not isinstance(spec, GeneralizedPoissonCovariateSpec):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"spec must be GeneralizedPoissonCovariateSpec, "
                f"got {type(spec).__name__}"
            )
