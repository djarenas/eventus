"""Count distributions.

A distribution is a mathematical concept — a pattern describing
how event counts are distributed across a population. It holds
parameters, validates them, and describes itself in plain language.

A distribution does not compute probabilities, fit data, simulate,
or plot. Those are the jobs of other objects.
"""

from abc import ABC, abstractmethod


class CountDistribution(ABC):
    """A mathematical distribution over non-negative integer counts.

    A distribution has parameters and can describe what they mean.
    That is all it does. It is a concept, not a tool.

    Attributes:
        params (dict): The distribution's parameters.

    Class Attributes:
        REGISTRY (dict): Maps distribution names to subclass types.
    """

    # Attribute Declarations
    params: dict

    # Subclass registry
    REGISTRY: dict = {}

    def __init__(self, params: dict):
        """Create a distribution and validate its parameters.

        Args:
            params: Dict of parameter names to values.

        Raises:
            ValueError: If parameters are missing or invalid.
        """
        self.params = params
        self.validate_parameters()

    @classmethod
    def build_from_yaml(cls, path: str) -> "CountDistribution":
        """Create a distribution from a YAML file.

        Expected YAML format:
            distribution: PoissonDistribution
            parameters:
                lambda: 4.2

        Args:
            path: Path to the YAML file.

        Returns:
            A validated distribution instance.

        Raises:
            ValueError: If distribution type is unknown or params invalid.
        """
        import yaml
        with open(path, "r") as f:
            config = yaml.safe_load(f)

        dist_name = config.get("distribution")
        if dist_name not in cls.REGISTRY:
            raise ValueError(
                f"Unknown distribution '{dist_name}'. "
                f"Available: {list(cls.REGISTRY.keys())}"
            )

        dist_cls = cls.REGISTRY[dist_name]
        return dist_cls(config["parameters"])

    @classmethod
    def register(cls, name: str, subclass) -> None:
        """Register a distribution subclass.

        Args:
            name: String identifier (typically class name).
            subclass: The distribution class to register.
        """
        cls.REGISTRY[name] = subclass

    # ---- Abstract methods ----

    @abstractmethod
    def validate_parameters(self) -> None:
        """Check that this distribution's parameters are valid.

        Raises:
            ValueError: If parameters are missing or out of range.
        """
        ...

    @abstractmethod
    def describe(self) -> list[str]:
        """Describe this distribution in plain language.

        Returns:
            List of human-readable strings explaining what the
            parameters mean. No jargon, no data references.
        """
        ...

    @abstractmethod
    def parameter_names(self) -> list[str]:
        """List the names of this distribution's parameters.

        Returns:
            e.g. ['lambda'] or ['alpha', 'beta']
        """
        ...

    # ---- Concrete methods ----

    def to_dict(self) -> dict:
        """Export as a plain dictionary.

        Returns:
            Dict with distribution name and parameters.
        """
        return {
            "distribution": self.__class__.__name__,
            "parameters": self.params.copy(),
        }

    def __repr__(self) -> str:
        param_str = ", ".join(
            f"{name}={self.params[name]:.4f}"
            for name in self.parameter_names()
            if name in self.params
        )
        return f"{self.__class__.__name__}({param_str})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, CountDistribution):
            return False
        return (self.__class__ == other.__class__
                and self.params == other.params)


# =====================================================================
#  Poisson
# =====================================================================

class PoissonDistribution(CountDistribution):
    """Poisson distribution.

    All individuals share the same constant event rate.
    Mean equals variance.

    Parameters:
        lambda (float): Constant event rate. Must be positive.
    """

    def validate_parameters(self) -> None:
        if "lambda" not in self.params:
            raise ValueError("PoissonDistribution requires 'lambda' parameter")
        if self.params["lambda"] <= 0:
            raise ValueError(f"Lambda must be positive, got {self.params['lambda']}")

    def describe(self) -> list[str]:
        lam = self.params["lambda"]
        return [
            "Poisson distribution",
            f"Rate (lambda): {lam:.4f}",
            "All individuals share the same constant event rate",
            f"Mean = Variance = {lam:.4f}",
        ]

    def parameter_names(self) -> list[str]:
        return ["lambda"]


CountDistribution.register("PoissonDistribution", PoissonDistribution)


# =====================================================================
#  Poisson-Gamma (Negative Binomial)
# =====================================================================

class PoissonGammaDistribution(CountDistribution):
    """Poisson-Gamma distribution.

    Each individual draws their own event rate from a Gamma
    distribution. This produces overdispersion (variance > mean).

    Generative story:
        1. Each person has a rate drawn from Gamma(alpha, beta)
        2. Their events follow Poisson(rate)

    Parameters:
        alpha (float): Gamma shape. Controls rate heterogeneity.
            Small alpha = high heterogeneity. Must be positive.
        beta (float): Gamma rate. Scales overall event rate.
            Must be positive.
    """

    def validate_parameters(self) -> None:
        if "alpha" not in self.params or "beta" not in self.params:
            raise ValueError(
                "PoissonGammaDistribution requires 'alpha' and 'beta' parameters"
            )
        if self.params["alpha"] <= 0:
            raise ValueError(f"Alpha must be positive, got {self.params['alpha']}")
        if self.params["beta"] <= 0:
            raise ValueError(f"Beta must be positive, got {self.params['beta']}")

    def describe(self) -> list[str]:
        alpha = self.params["alpha"]
        beta = self.params["beta"]
        mean = alpha / beta
        cv = 1 / (alpha ** 0.5)
        return [
            "Poisson-Gamma distribution",
            f"Gamma shape (alpha): {alpha:.4f}",
            f"Gamma rate (beta): {beta:.4f}",
            f"Each person draws their own rate from Gamma({alpha:.2f}, {beta:.2f})",
            f"Population mean rate: {mean:.4f}",
            f"Rate heterogeneity (CV): {cv:.4f}",
        ]

    def parameter_names(self) -> list[str]:
        return ["alpha", "beta"]


CountDistribution.register("PoissonGammaDistribution", PoissonGammaDistribution)


# =====================================================================
#  Geometric
# =====================================================================

class GeometricDistribution(CountDistribution):
    """Geometric distribution.

    Special case of Poisson-Gamma where person-level rates follow
    an Exponential distribution (maximum heterogeneity).

    Parameters:
        p (float): Success probability. Must be between 0 and 1.
    """

    def validate_parameters(self) -> None:
        if "p" not in self.params:
            raise ValueError("GeometricDistribution requires 'p' parameter")
        if not 0 < self.params["p"] < 1:
            raise ValueError(f"p must be between 0 and 1, got {self.params['p']}")

    def describe(self) -> list[str]:
        p = self.params["p"]
        mean = (1 - p) / p
        return [
            "Geometric distribution",
            f"Parameter (p): {p:.4f}",
            "Person-level rates follow an Exponential (maximum heterogeneity)",
            f"Equivalent to Poisson-Gamma with alpha=1",
            f"Expected mean: {mean:.4f}",
        ]

    def parameter_names(self) -> list[str]:
        return ["p"]


CountDistribution.register("GeometricDistribution", GeometricDistribution)


# =====================================================================
#  Zero-Inflated Poisson (ZIP)
# =====================================================================

class ZIPDistribution(CountDistribution):
    """Zero-Inflated Poisson distribution.

    Some individuals are structural zeros — they will never have
    events. The rest follow a standard Poisson process.

    Generative story:
        1. With probability pi, a person is a structural zero
        2. With probability (1 - pi), they follow Poisson(lambda)

    Parameters:
        pi (float): Probability of being a structural zero. [0, 1).
        lambda (float): Poisson rate for the active group. Must be positive.
    """

    def validate_parameters(self) -> None:
        if "pi" not in self.params or "lambda" not in self.params:
            raise ValueError(
                "ZIPDistribution requires 'pi' and 'lambda' parameters"
            )
        if not 0 <= self.params["pi"] < 1:
            raise ValueError(f"pi must be in [0, 1), got {self.params['pi']}")
        if self.params["lambda"] <= 0:
            raise ValueError(f"Lambda must be positive, got {self.params['lambda']}")

    def describe(self) -> list[str]:
        pi = self.params["pi"]
        lam = self.params["lambda"]
        return [
            "Zero-Inflated Poisson distribution",
            f"Zero-inflation (pi): {pi:.4f}",
            f"Active rate (lambda): {lam:.4f}",
            f"{pi * 100:.1f}% of individuals will never have events",
            f"Remaining {(1 - pi) * 100:.1f}% follow Poisson(lambda={lam:.2f})",
        ]

    def parameter_names(self) -> list[str]:
        return ["pi", "lambda"]


CountDistribution.register("ZIPDistribution", ZIPDistribution)


# =====================================================================
#  Zero-Inflated Poisson-Gamma (ZIPG)
# =====================================================================

class ZIPGDistribution(CountDistribution):
    """Zero-Inflated Poisson-Gamma distribution.

    Combines structural zeros with heterogeneous rates among
    active individuals. The most flexible standard parametric model.

    Generative story:
        1. With probability pi, a person is a structural zero
        2. With probability (1 - pi), they draw a rate from Gamma(alpha, beta)
        3. Their events follow Poisson(rate)

    Parameters:
        pi (float): Probability of being a structural zero. [0, 1).
        alpha (float): Gamma shape for active group. Must be positive.
        beta (float): Gamma rate for active group. Must be positive.
    """

    def validate_parameters(self) -> None:
        required = ["pi", "alpha", "beta"]
        missing = [p for p in required if p not in self.params]
        if missing:
            raise ValueError(f"ZIPGDistribution requires parameters: {missing}")
        if not 0 <= self.params["pi"] < 1:
            raise ValueError(f"pi must be in [0, 1), got {self.params['pi']}")
        if self.params["alpha"] <= 0:
            raise ValueError(f"Alpha must be positive, got {self.params['alpha']}")
        if self.params["beta"] <= 0:
            raise ValueError(f"Beta must be positive, got {self.params['beta']}")

    def describe(self) -> list[str]:
        pi = self.params["pi"]
        alpha = self.params["alpha"]
        beta = self.params["beta"]
        mean = alpha / beta
        cv = 1 / (alpha ** 0.5)
        return [
            "Zero-Inflated Poisson-Gamma distribution",
            f"Zero-inflation (pi): {pi:.4f}",
            f"Gamma shape (alpha): {alpha:.4f}",
            f"Gamma rate (beta): {beta:.4f}",
            f"{pi * 100:.1f}% of individuals are structural zeros",
            f"Active persons draw rates from Gamma({alpha:.2f}, {beta:.2f})",
            f"Active population mean rate: {mean:.4f}",
            f"Active rate heterogeneity (CV): {cv:.4f}",
        ]

    def parameter_names(self) -> list[str]:
        return ["pi", "alpha", "beta"]


CountDistribution.register("ZIPGDistribution", ZIPGDistribution)


# =====================================================================
#  Generalized Poisson
# =====================================================================

class GeneralizedPoissonDistribution(CountDistribution):
    """Generalized Poisson distribution.

    Handles both overdispersion and underdispersion through a
    single dispersion parameter lambda.

    Parameters:
        theta (float): Base rate. Must be positive.
        lambda (float): Dispersion parameter. Must be in (-1, 1).
            lambda > 0: overdispersion
            lambda = 0: standard Poisson
            lambda < 0: underdispersion
    """

    def validate_parameters(self) -> None:
        if "theta" not in self.params or "lambda" not in self.params:
            raise ValueError(
                "GeneralizedPoissonDistribution requires 'theta' and 'lambda' parameters"
            )
        if self.params["theta"] <= 0:
            raise ValueError(f"Theta must be positive, got {self.params['theta']}")
        if not -1 < self.params["lambda"] < 1:
            raise ValueError(
                f"Lambda must be in (-1, 1), got {self.params['lambda']}"
            )

    def describe(self) -> list[str]:
        theta = self.params["theta"]
        lam = self.params["lambda"]
        mean = theta / (1 - lam) if lam != 1 else float("inf")

        lines = [
            "Generalized Poisson distribution",
            f"Base rate (theta): {theta:.4f}",
            f"Dispersion (lambda): {lam:.4f}",
            f"Expected mean: {mean:.4f}",
        ]

        if abs(lam) < 0.05:
            lines.append("Near standard Poisson (lambda close to 0)")
        elif lam > 0:
            lines.append("Overdispersed (variance > mean)")
        else:
            lines.append("Underdispersed (variance < mean)")

        return lines

    def parameter_names(self) -> list[str]:
        return ["theta", "lambda"]


CountDistribution.register("GeneralizedPoissonDistribution", GeneralizedPoissonDistribution)


# =====================================================================
#  Poisson Mixture
# =====================================================================

class PoissonMixtureDistribution(CountDistribution):
    """Finite mixture of Poisson distributions.

    The population consists of K distinct groups, each with its own
    event rate. The model discovers both the group rates and the
    proportion of the population in each group.

    Parameters:
        k (int): Number of mixture components.
        w1, w2, ..., wK (float): Component weights. Must sum to 1.
        lambda1, lambda2, ..., lambdaK (float): Component rates.
            Must be positive.
    """

    def validate_parameters(self) -> None:
        if "k" not in self.params:
            raise ValueError("PoissonMixtureDistribution requires 'k' parameter")

        k = self.params["k"]
        if not isinstance(k, int) or k < 1:
            raise ValueError(f"k must be a positive integer, got {k}")

        weights = []
        for j in range(1, k + 1):
            w_key = f"w{j}"
            l_key = f"lambda{j}"
            if w_key not in self.params:
                raise ValueError(f"Missing weight parameter '{w_key}'")
            if l_key not in self.params:
                raise ValueError(f"Missing rate parameter '{l_key}'")
            if self.params[w_key] < 0 or self.params[w_key] > 1:
                raise ValueError(
                    f"{w_key} must be in [0, 1], got {self.params[w_key]}"
                )
            if self.params[l_key] <= 0:
                raise ValueError(
                    f"{l_key} must be positive, got {self.params[l_key]}"
                )
            weights.append(self.params[w_key])

        if abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1, got {sum(weights)}")

    def describe(self) -> list[str]:
        k = self.params["k"]
        lines = [
            f"Poisson Mixture distribution (K={k})",
            f"Population consists of {k} distinct groups:",
        ]
        for j in range(1, k + 1):
            w = self.params[f"w{j}"]
            lam = self.params[f"lambda{j}"]
            lines.append(
                f"  Group {j}: {w * 100:.1f}% of population, rate={lam:.4f}"
            )
        return lines

    def parameter_names(self) -> list[str]:
        k = self.params.get("k", 0)
        names = ["k"]
        for j in range(1, k + 1):
            names.extend([f"w{j}", f"lambda{j}"])
        return names


CountDistribution.register("PoissonMixtureDistribution", PoissonMixtureDistribution)


# =====================================================================
#  Hurdle Poisson
# =====================================================================

class HurdlePoissonDistribution(CountDistribution):
    """Hurdle Poisson distribution.

    Two-stage model: first decide if a person has any events at all,
    then if they do, how many. All zeros come from the same process
    (not crossing the hurdle).

    Generative story:
        1. With probability pi, a person crosses the hurdle (has events)
        2. Given they crossed, count follows zero-truncated Poisson(lambda)

    Parameters:
        pi (float): Probability of crossing the hurdle. (0, 1].
        lambda (float): Poisson rate for those who crossed. Must be positive.
    """

    def validate_parameters(self) -> None:
        if "pi" not in self.params or "lambda" not in self.params:
            raise ValueError(
                "HurdlePoissonDistribution requires 'pi' and 'lambda' parameters"
            )
        if not 0 < self.params["pi"] <= 1:
            raise ValueError(f"pi must be in (0, 1], got {self.params['pi']}")
        if self.params["lambda"] <= 0:
            raise ValueError(
                f"Lambda must be positive, got {self.params['lambda']}"
            )

    def describe(self) -> list[str]:
        pi = self.params["pi"]
        lam = self.params["lambda"]
        return [
            "Hurdle Poisson distribution",
            f"Hurdle probability (pi): {pi:.4f}",
            f"Active rate (lambda): {lam:.4f}",
            f"{pi * 100:.1f}% of individuals cross the hurdle (have events)",
            f"{(1 - pi) * 100:.1f}% never have events",
            "All zeros come from not crossing the hurdle",
        ]

    def parameter_names(self) -> list[str]:
        return ["pi", "lambda"]


CountDistribution.register("HurdlePoissonDistribution", HurdlePoissonDistribution)


# =====================================================================
#  Hurdle Poisson-Gamma
# =====================================================================

class HurdlePoissonGammaDistribution(CountDistribution):
    """Hurdle Poisson-Gamma distribution.

    Two-stage model with heterogeneous rates among active individuals.
    Combines a hurdle mechanism with Gamma-distributed person-level rates.

    Generative story:
        1. With probability pi, a person crosses the hurdle
        2. They draw a personal rate from Gamma(alpha, beta)
        3. Their count follows zero-truncated Poisson(rate)

    Parameters:
        pi (float): Probability of crossing the hurdle. (0, 1].
        alpha (float): Gamma shape for active group. Must be positive.
        beta (float): Gamma rate for active group. Must be positive.
    """

    def validate_parameters(self) -> None:
        required = ["pi", "alpha", "beta"]
        missing = [p for p in required if p not in self.params]
        if missing:
            raise ValueError(
                f"HurdlePoissonGammaDistribution requires parameters: {missing}"
            )
        if not 0 < self.params["pi"] <= 1:
            raise ValueError(f"pi must be in (0, 1], got {self.params['pi']}")
        if self.params["alpha"] <= 0:
            raise ValueError(f"Alpha must be positive, got {self.params['alpha']}")
        if self.params["beta"] <= 0:
            raise ValueError(f"Beta must be positive, got {self.params['beta']}")

    def describe(self) -> list[str]:
        pi = self.params["pi"]
        alpha = self.params["alpha"]
        beta = self.params["beta"]
        mean = alpha / beta
        cv = 1 / (alpha ** 0.5)
        return [
            "Hurdle Poisson-Gamma distribution",
            f"Hurdle probability (pi): {pi:.4f}",
            f"Gamma shape (alpha): {alpha:.4f}",
            f"Gamma rate (beta): {beta:.4f}",
            f"{pi * 100:.1f}% of individuals cross the hurdle",
            f"Active persons draw rates from Gamma({alpha:.2f}, {beta:.2f})",
            f"Active population mean rate: {mean:.4f}",
            f"Active rate heterogeneity (CV): {cv:.4f}",
        ]

    def parameter_names(self) -> list[str]:
        return ["pi", "alpha", "beta"]


CountDistribution.register("HurdlePoissonGammaDistribution", HurdlePoissonGammaDistribution)
