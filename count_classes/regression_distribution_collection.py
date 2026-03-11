"""Regression distribution collection.

A collection holds multiple fitted regression distributions and
provides methods to compare them, save to YAML, and load from YAML.

The key method is coefficient_comparison_table() which produces
a single table showing all coefficients across all models — the
primary output for multiverse analysis.
"""

import yaml
import pandas as pd

from .count_regression_distributions import CountRegressionDistribution
from .count_regression_specs import (
    CountRegressionSpec,
    PoissonRegressionSpec,
    PoissonGammaRegressionSpec,
    GeometricRegressionSpec,
    ZIPRegressionSpec,
    ZIPGRegressionSpec,
    GeneralizedPoissonRegressionSpec,
)

# Registry mapping class name strings to classes for YAML loading
_REGRESSION_DIST_REGISTRY = {}
_REGRESSION_SPEC_REGISTRY = {}


def _build_registries():
    """Build registries on first use to avoid circular imports."""
    global _REGRESSION_DIST_REGISTRY, _REGRESSION_SPEC_REGISTRY

    if _REGRESSION_DIST_REGISTRY:
        return

    from .count_regression_distributions import (
        PoissonRegressionDistribution,
        PoissonGammaRegressionDistribution,
        GeometricRegressionDistribution,
        ZIPRegressionDistribution,
        ZIPGRegressionDistribution,
        GeneralizedPoissonRegressionDistribution,
    )
    from .count_regression_distribution_hurdle import (
        HurdlePoissonRegressionDistribution,
        HurdlePoissonGammaRegressionDistribution,
    )
    from .count_regression_distribution_mixture import (
        PoissonMixtureRegressionDistribution,
    )
    from .count_regression_spec_hurdle import (
        HurdlePoissonRegressionSpec,
        HurdlePoissonGammaRegressionSpec,
    )
    from .count_regression_spec_mixture import (
        PoissonMixtureRegressionSpec,
    )

    _REGRESSION_DIST_REGISTRY.update({
        "PoissonRegressionDistribution": PoissonRegressionDistribution,
        "PoissonGammaRegressionDistribution": PoissonGammaRegressionDistribution,
        "GeometricRegressionDistribution": GeometricRegressionDistribution,
        "ZIPRegressionDistribution": ZIPRegressionDistribution,
        "ZIPGRegressionDistribution": ZIPGRegressionDistribution,
        "GeneralizedPoissonRegressionDistribution": GeneralizedPoissonRegressionDistribution,
        "HurdlePoissonRegressionDistribution": HurdlePoissonRegressionDistribution,
        "HurdlePoissonGammaRegressionDistribution": HurdlePoissonGammaRegressionDistribution,
        "PoissonMixtureRegressionDistribution": PoissonMixtureRegressionDistribution,
    })

    _REGRESSION_SPEC_REGISTRY.update({
        "PoissonRegressionSpec": PoissonRegressionSpec,
        "PoissonGammaRegressionSpec": PoissonGammaRegressionSpec,
        "GeometricRegressionSpec": GeometricRegressionSpec,
        "ZIPRegressionSpec": ZIPRegressionSpec,
        "ZIPGRegressionSpec": ZIPGRegressionSpec,
        "GeneralizedPoissonRegressionSpec": GeneralizedPoissonRegressionSpec,
        "HurdlePoissonRegressionSpec": HurdlePoissonRegressionSpec,
        "HurdlePoissonGammaRegressionSpec": HurdlePoissonGammaRegressionSpec,
        "PoissonMixtureRegressionSpec": PoissonMixtureRegressionSpec,
    })


class RegressionDistributionCollection:
    """A validated group of fitted regression distributions.

    Holds named regression distributions and provides methods to
    compare coefficients across models, save to YAML, and load
    from YAML.

    Attributes:
        distributions (dict): Maps name to CountRegressionDistribution.

    Example:
        >>> collection = RegressionDistributionCollection(fitted)
        >>> print(collection.coefficient_comparison_table())
        >>> collection.save_to_yaml("results.yaml")

    Example (load):
        >>> loaded = RegressionDistributionCollection.build_from_yaml("results.yaml")
    """

    _ERROR_PREFIX = "[RegressionDistributionCollection]"

    # Attribute Declarations
    distributions: dict

    def __init__(self, distributions: dict):
        """Create a collection from a dict of regression distributions.

        Args:
            distributions: Dict mapping names to
                CountRegressionDistribution instances.

        Raises:
            TypeError: If not a dict or values are wrong type.
            ValueError: If empty.
        """
        self._validate(distributions)
        self.distributions = distributions

    def _validate(self, distributions) -> None:
        """Validate the distributions dict.

        Raises:
            TypeError: If not a dict or values are wrong type.
            ValueError: If empty.
        """
        if not isinstance(distributions, dict):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Expected dict, got {type(distributions).__name__}"
            )
        if len(distributions) == 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Distributions dict cannot be empty"
            )
        for name, dist in distributions.items():
            if not isinstance(name, str):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Distribution name must be a string, "
                    f"got {type(name).__name__}"
                )
            if not isinstance(dist, CountRegressionDistribution):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Distribution '{name}' must be a "
                    f"CountRegressionDistribution, "
                    f"got {type(dist).__name__}"
                )

    # ---- Comparison ----

    def coefficient_comparison_table(self) -> pd.DataFrame:
        """Produce a table comparing coefficients across all models.

        Each column is a model-component pair (e.g., "PoissonGamma_rate").
        Each row is a covariate. Values are coefficients. Missing
        covariates show as NaN.

        Returns:
            DataFrame with covariates as rows and model-components
            as columns.
        """
        all_data = {}

        for model_name, dist in self.distributions.items():
            for comp_name, comp_coeffs in dist.coefficients.items():
                column_name = f"{model_name}_{comp_name}"
                all_data[column_name] = comp_coeffs

        df = pd.DataFrame(all_data)
        df.index.name = "covariate"

        # Sort rows: intercept first, then alphabetical
        rows = list(df.index)
        if "intercept" in rows:
            rows.remove("intercept")
            rows = ["intercept"] + sorted(rows)
        else:
            rows = sorted(rows)
        df = df.loc[rows]

        return df

    def coefficient_stability_report(self) -> pd.DataFrame:
        """Analyze how stable each covariate's effect is across models.

        For each covariate that appears in rate components, computes
        the mean, std, min, max of its coefficient across models.
        Stable coefficients (low std) indicate robust findings.

        Returns:
            DataFrame with covariates as rows and statistics as columns.
        """
        # Collect rate coefficients across models
        rate_coeffs = {}
        for model_name, dist in self.distributions.items():
            for comp_name, comp_coeffs in dist.coefficients.items():
                if "rate" in comp_name:
                    for cov_name, value in comp_coeffs.items():
                        if cov_name not in rate_coeffs:
                            rate_coeffs[cov_name] = {}
                        rate_coeffs[cov_name][model_name] = value

        rows = []
        for cov_name, model_values in rate_coeffs.items():
            values = list(model_values.values())
            rows.append({
                "covariate": cov_name,
                "n_models": len(values),
                "mean": round(sum(values) / len(values), 6),
                "std": round(pd.Series(values).std(), 6),
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "range": round(max(values) - min(values), 6),
            })

        df = pd.DataFrame(rows).sort_values("std").reset_index(drop=True)
        return df

    # ---- Description ----

    def describe_all(self) -> dict:
        """Get descriptions from all distributions.

        Returns:
            Dict mapping name to list of description strings.
        """
        return {
            name: dist.describe()
            for name, dist in self.distributions.items()
        }

    def summarize(self) -> str:
        """Generate a human-readable summary.

        Returns:
            Formatted multi-line string.
        """
        lines = [
            f"{'=' * 65}",
            f"  Regression Distribution Collection",
            f"{'=' * 65}",
            f"  Models: {len(self.distributions)}",
            f"",
        ]

        for name, dist in self.distributions.items():
            lines.append(f"  {name}:")
            for desc_line in dist.describe():
                lines.append(f"    {desc_line}")
            lines.append("")

        # Stability summary
        stability = self.coefficient_stability_report()
        if len(stability) > 0:
            lines.append("  Coefficient Stability (rate components):")
            lines.append(f"    Most stable: {stability.iloc[0]['covariate']} "
                         f"(std={stability.iloc[0]['std']:.4f})")
            lines.append(f"    Least stable: {stability.iloc[-1]['covariate']} "
                         f"(std={stability.iloc[-1]['std']:.4f})")

        lines.append(f"{'=' * 65}")
        return "\n".join(lines)

    # ---- YAML Save/Load ----

    def save_to_yaml(self, path: str) -> None:
        """Save the collection to a YAML file.

        Args:
            path: File path to save to.

        Raises:
            TypeError: If path is not a string.
            RuntimeError: If writing fails.
        """
        if not isinstance(path, str):
            raise TypeError(
                f"{self._ERROR_PREFIX} save_to_yaml: "
                f"path must be a string, got {type(path).__name__}"
            )

        entries = []
        for name, dist in self.distributions.items():
            entry = dist.to_dict()
            entry["name"] = name
            entries.append(entry)

        output = {"regression_distributions": entries}

        try:
            with open(path, "w") as f:
                yaml.dump(output, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise RuntimeError(
                f"{self._ERROR_PREFIX} save_to_yaml: "
                f"Failed to write to '{path}': {e}"
            )

    @classmethod
    def build_from_yaml(cls, path: str) -> "RegressionDistributionCollection":
        """Load a collection from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            A validated RegressionDistributionCollection.

        Raises:
            TypeError: If path is not a string.
            FileNotFoundError: If file does not exist.
            ValueError: If YAML is malformed or contains unknown types.
        """
        _build_registries()

        if not isinstance(path, str):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"path must be a string, got {type(path).__name__}"
            )

        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"File not found: '{path}'"
            )
        except yaml.YAMLError as e:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Failed to parse YAML at '{path}': {e}"
            )

        cls._validate_yaml(config, path)

        distributions = {}
        for i, entry in enumerate(config["regression_distributions"]):
            name = entry.get("name", f"model_{i}")
            dist = cls._build_distribution_from_entry(entry, i, path)
            distributions[name] = dist

        return cls(distributions)

    @classmethod
    def _validate_yaml(cls, config, path: str) -> None:
        """Validate top-level YAML structure."""
        if not isinstance(config, dict):
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must be a dictionary"
            )
        if "regression_distributions" not in config:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"YAML at '{path}' must have 'regression_distributions' key"
            )
        if not isinstance(config["regression_distributions"], list):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'regression_distributions' must be a list"
            )
        if len(config["regression_distributions"]) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"'regression_distributions' list cannot be empty"
            )

    @classmethod
    def _build_distribution_from_entry(cls, entry: dict, index: int,
                                         path: str) -> CountRegressionDistribution:
        """Build a single regression distribution from a YAML entry.

        Args:
            entry: Dict with distribution, spec, and coefficients.
            index: Entry index for error messages.
            path: File path for error messages.

        Returns:
            A CountRegressionDistribution instance.
        """
        # Validate entry structure
        if "distribution" not in entry:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Entry {index} in '{path}' missing 'distribution' key"
            )
        if "spec" not in entry:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Entry {index} in '{path}' missing 'spec' key"
            )
        if "coefficients" not in entry:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Entry {index} in '{path}' missing 'coefficients' key"
            )

        # Look up distribution class
        dist_class_name = entry["distribution"]
        if dist_class_name not in _REGRESSION_DIST_REGISTRY:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Unknown distribution '{dist_class_name}' in entry {index}. "
                f"Known: {list(_REGRESSION_DIST_REGISTRY.keys())}"
            )

        # Look up spec class
        spec_info = entry["spec"]
        spec_class_name = spec_info["spec"]
        if spec_class_name not in _REGRESSION_SPEC_REGISTRY:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Unknown spec '{spec_class_name}' in entry {index}. "
                f"Known: {list(_REGRESSION_SPEC_REGISTRY.keys())}"
            )

        # Rebuild spec from components
        spec_cls = _REGRESSION_SPEC_REGISTRY[spec_class_name]
        components = spec_info["components"]
        spec = spec_cls(components)

        # Rebuild distribution
        dist_cls = _REGRESSION_DIST_REGISTRY[dist_class_name]
        coefficients = entry["coefficients"]
        dist = dist_cls(spec=spec, coefficients=coefficients)

        return dist

    # ---- Access ----

    def get(self, name: str) -> CountRegressionDistribution:
        """Retrieve a single distribution by name.

        Args:
            name: Distribution name.

        Returns:
            The CountRegressionDistribution instance.

        Raises:
            KeyError: If name not found.
        """
        if name not in self.distributions:
            raise KeyError(
                f"{self._ERROR_PREFIX} get: "
                f"'{name}' not in collection. "
                f"Available: {list(self.distributions.keys())}"
            )
        return self.distributions[name]

    def names(self) -> list:
        """Return list of all distribution names."""
        return list(self.distributions.keys())

    # ---- Dunder methods ----

    def __iter__(self):
        """Iterate over (name, distribution) pairs."""
        return iter(self.distributions.items())

    def __len__(self) -> int:
        return len(self.distributions)

    def __contains__(self, name: str) -> bool:
        return name in self.distributions

    def __repr__(self) -> str:
        names = list(self.distributions.keys())
        return f"RegressionDistributionCollection({len(names)} distributions: {names})"
