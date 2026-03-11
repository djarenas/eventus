"""Count regression specs — base class and simple specs.

A regression spec defines what a model should look like before
fitting. It says which covariates go into which model component.
It does not have coefficients — those come from fitting.

A spec is a model design choice. It answers the question:
"What do I want to try?"
"""

from abc import ABC, abstractmethod


class CountRegressionSpec(ABC):
    """Base class for all count regression specifications.

    A spec defines which covariates go into which model component.
    Each subclass knows what components its model type requires
    and validates accordingly.

    Attributes:
        components (dict): Maps component name to list of covariate
            names. e.g. {"rate": ["age", "BMI"], "dispersion": ["age"]}

    Example:
        >>> spec = PoissonRegressionSpec(rate_covariates=["age", "BMI"])
        >>> spec.describe()
        ['Poisson regression spec',
         '  rate: age, BMI']
    """

    _ERROR_PREFIX = "[CountRegressionSpec]"

    # Attribute Declarations
    components: dict

    def __init__(self, components: dict):
        """Create a spec and validate it.

        Args:
            components: Dict mapping component names to covariate lists.

        Raises:
            TypeError: If components is wrong type.
            ValueError: If required components are missing or invalid.
        """
        self._validate_components_type(components)
        self._validate_required_components(components)
        self._validate_covariate_lists(components)
        self.components = components

    def _validate_components_type(self, components) -> None:
        """Check that components is a dict."""
        if not isinstance(components, dict):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"components must be a dict, got {type(components).__name__}"
            )

    def _validate_covariate_lists(self, components) -> None:
        """Check that each component value is a list of strings."""
        for comp_name, covariates in components.items():
            if not isinstance(covariates, list):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Component '{comp_name}' covariates must be a list, "
                    f"got {type(covariates).__name__}"
                )
            for i, cov in enumerate(covariates):
                if not isinstance(cov, str):
                    raise TypeError(
                        f"{self._ERROR_PREFIX} __init__: "
                        f"Component '{comp_name}' covariate {i} must be a string, "
                        f"got {type(cov).__name__}"
                    )
            # Check for duplicates within a component
            duplicates = set(c for c in covariates if covariates.count(c) > 1)
            if duplicates:
                raise ValueError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Component '{comp_name}' has duplicate covariates: {duplicates}"
                )

    @abstractmethod
    def _validate_required_components(self, components: dict) -> None:
        """Check that the required component names are present.

        Each subclass defines what components it requires.

        Raises:
            ValueError: If required components are missing or
                unexpected components are present.
        """
        ...

    @abstractmethod
    def required_components(self) -> list:
        """Return the list of required component names for this model.

        Returns:
            e.g. ["rate"] or ["rate", "dispersion"] or ["hurdle", "count"]
        """
        ...

    def component_names(self) -> list:
        """Return the list of component names in this spec.

        Returns:
            List of component name strings.
        """
        return list(self.components.keys())

    def all_covariates(self) -> list:
        """Return a flat list of all covariates across all components.

        May contain duplicates if the same covariate appears in
        multiple components (which is valid).

        Returns:
            List of covariate name strings.
        """
        covs = []
        for comp_covs in self.components.values():
            covs.extend(comp_covs)
        return covs

    def unique_covariates(self) -> set:
        """Return the set of unique covariates across all components.

        Returns:
            Set of covariate name strings.
        """
        return set(self.all_covariates())

    def get_component_covariates(self, component_name: str) -> list:
        """Get the covariate list for a specific component.

        Args:
            component_name: Name of the component.

        Returns:
            List of covariate names.

        Raises:
            KeyError: If component name not in spec.
        """
        if component_name not in self.components:
            raise KeyError(
                f"{self._ERROR_PREFIX} get_component_covariates: "
                f"'{component_name}' not in spec. "
                f"Available: {self.component_names()}"
            )
        return self.components[component_name]

    def describe(self) -> list:
        """Describe this spec in plain language.

        Returns:
            List of descriptive strings.
        """
        lines = [f"{self.__class__.__name__}"]
        for comp_name, covariates in self.components.items():
            cov_str = ", ".join(covariates) if covariates else "(intercept only)"
            lines.append(f"  {comp_name}: {cov_str}")
        return lines

    def to_dict(self) -> dict:
        """Export as a plain dictionary.

        Returns:
            Dict with model type and components.
        """
        return {
            "spec": self.__class__.__name__,
            "components": {k: list(v) for k, v in self.components.items()},
        }

    def __repr__(self) -> str:
        comp_summary = ", ".join(
            f"{name}=[{len(covs)} covs]"
            for name, covs in self.components.items()
        )
        return f"{self.__class__.__name__}({comp_summary})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, CountRegressionSpec):
            return False
        return (self.__class__ == other.__class__
                and self.components == other.components)


# ---- Helper for simple component validation ----

def _validate_exact_components(components: dict, required: set, class_name: str) -> None:
    """Validate that components has exactly the required keys.

    Args:
        components: The components dict to validate.
        required: Set of required component names.
        class_name: Name of the spec class for error messages.

    Raises:
        ValueError: If components are missing or unexpected.
    """
    present = set(components.keys())
    missing = required - present
    unexpected = present - required

    if missing:
        raise ValueError(
            f"[{class_name}] __init__: "
            f"Missing required components: {missing}. "
            f"Required: {required}"
        )
    if unexpected:
        raise ValueError(
            f"[{class_name}] __init__: "
            f"Unexpected components: {unexpected}. "
            f"Allowed: {required}"
        )


# =====================================================================
#  Poisson
# =====================================================================

class PoissonRegressionSpec(CountRegressionSpec):
    """Spec for Poisson regression.

    One component: rate.
    rate = exp(intercept + b1*age + b2*BMI + ...)
    """

    _REQUIRED = {"rate"}

    def __init__(self, rate_covariates: list):
        """Create a Poisson regression spec.

        Args:
            rate_covariates: List of covariate names for the rate component.
        """
        super().__init__({"rate": rate_covariates})

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  Poisson-Gamma
# =====================================================================

class PoissonGammaRegressionSpec(CountRegressionSpec):
    """Spec for Poisson-Gamma regression.

    Two components: rate and dispersion.
    rate = exp(intercept + b1*age + ...)
    dispersion = exp(intercept + g1*age + ...)
    """

    _REQUIRED = {"rate", "dispersion"}

    def __init__(self, rate_covariates: list, dispersion_covariates: list):
        """Create a Poisson-Gamma regression spec.

        Args:
            rate_covariates: Covariates for the rate component.
            dispersion_covariates: Covariates for the dispersion component.
        """
        super().__init__({
            "rate": rate_covariates,
            "dispersion": dispersion_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  Geometric
# =====================================================================

class GeometricRegressionSpec(CountRegressionSpec):
    """Spec for Geometric regression.

    One component: rate.
    Special case of PoissonGamma with fixed dispersion.
    """

    _REQUIRED = {"rate"}

    def __init__(self, rate_covariates: list):
        """Create a Geometric regression spec.

        Args:
            rate_covariates: Covariates for the rate component.
        """
        super().__init__({"rate": rate_covariates})

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  ZIP
# =====================================================================

class ZIPRegressionSpec(CountRegressionSpec):
    """Spec for Zero-Inflated Poisson regression.

    Two components: rate and zero_inflation.
    rate = exp(intercept + b1*age + ...)
    P(structural zero) = logit(intercept + z1*previous_dx + ...)
    """

    _REQUIRED = {"rate", "zero_inflation"}

    def __init__(self, rate_covariates: list, zero_inflation_covariates: list):
        """Create a ZIP regression spec.

        Args:
            rate_covariates: Covariates for the rate component.
            zero_inflation_covariates: Covariates for the zero-inflation component.
        """
        super().__init__({
            "rate": rate_covariates,
            "zero_inflation": zero_inflation_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  ZIPG
# =====================================================================

class ZIPGRegressionSpec(CountRegressionSpec):
    """Spec for Zero-Inflated Poisson-Gamma regression.

    Three components: rate, dispersion, and zero_inflation.
    """

    _REQUIRED = {"rate", "dispersion", "zero_inflation"}

    def __init__(self, rate_covariates: list, dispersion_covariates: list,
                 zero_inflation_covariates: list):
        """Create a ZIPG regression spec.

        Args:
            rate_covariates: Covariates for the rate component.
            dispersion_covariates: Covariates for the dispersion component.
            zero_inflation_covariates: Covariates for the zero-inflation component.
        """
        super().__init__({
            "rate": rate_covariates,
            "dispersion": dispersion_covariates,
            "zero_inflation": zero_inflation_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonRegressionSpec(CountRegressionSpec):
    """Spec for Generalized Poisson regression.

    Two components: rate and dispersion.
    """

    _REQUIRED = {"rate", "dispersion"}

    def __init__(self, rate_covariates: list, dispersion_covariates: list):
        """Create a Generalized Poisson regression spec.

        Args:
            rate_covariates: Covariates for the rate component.
            dispersion_covariates: Covariates for the dispersion component.
        """
        super().__init__({
            "rate": rate_covariates,
            "dispersion": dispersion_covariates,
        })

    def _validate_required_components(self, components: dict) -> None:
        _validate_exact_components(components, self._REQUIRED, self.__class__.__name__)

    def required_components(self) -> list:
        return list(self._REQUIRED)
