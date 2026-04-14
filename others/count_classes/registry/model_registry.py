# =====================================================================
#  Master registry of all known models
# =====================================================================
from .count_distributions import (
    PoissonDistribution,
    PoissonGammaDistribution,
    GeometricDistribution,
    ZIPDistribution,
    ZIPGDistribution,
    GeneralizedPoissonDistribution,
    PoissonMixtureDistribution,
    HurdlePoissonDistribution,
    HurdlePoissonGammaDistribution,
)
from .count_distribution_computers import (
    PoissonComputer,
    PoissonGammaComputer,
    GeometricComputer,
    ZIPComputer,
    ZIPGComputer,
    GeneralizedPoissonComputer,
    PoissonMixtureComputer,
    HurdlePoissonComputer,
    HurdlePoissonGammaComputer,
)
from .count_distribution_simulators import (
    PoissonSimulator,
    PoissonGammaSimulator,
    GeometricSimulator,
    ZIPSimulator,
    ZIPGSimulator,
    GeneralizedPoissonSimulator,
    PoissonMixtureSimulator,
    HurdlePoissonSimulator,
    HurdlePoissonGammaSimulator,
)
from .count_distribution_fitters import (
    PoissonFitter,
    PoissonGammaFitter,
    GeometricFitter,
)
from .count_distribution_fitter_zip import ZIPFitter, ZIPGFitter
from .count_distribution_fitter_hurdle import HurdlePoissonFitter, HurdlePoissonGammaFitter
from .count_distribution_fitter_gp import GeneralizedPoissonFitter
from .count_distribution_fitter_mixture import PoissonMixtureFitter


MODEL_REGISTRY = {
    "Poisson": {
        "distribution": PoissonDistribution,
        "fitter": PoissonFitter,
        "simulator": PoissonSimulator,
        "computer": PoissonComputer,
    },
    "PoissonGamma": {
        "distribution": PoissonGammaDistribution,
        "fitter": PoissonGammaFitter,
        "simulator": PoissonGammaSimulator,
        "computer": PoissonGammaComputer,
    },
    "Geometric": {
        "distribution": GeometricDistribution,
        "fitter": GeometricFitter,
        "simulator": GeometricSimulator,
        "computer": GeometricComputer,
    },
    "ZIP": {
        "distribution": ZIPDistribution,
        "fitter": ZIPFitter,
        "simulator": ZIPSimulator,
        "computer": ZIPComputer,
    },
    "ZIPG": {
        "distribution": ZIPGDistribution,
        "fitter": ZIPGFitter,
        "simulator": ZIPGSimulator,
        "computer": ZIPGComputer,
    },
    "GeneralizedPoisson": {
        "distribution": GeneralizedPoissonDistribution,
        "fitter": GeneralizedPoissonFitter,
        "simulator": GeneralizedPoissonSimulator,
        "computer": GeneralizedPoissonComputer,
    },
    "PoissonMixture": {
        "distribution": PoissonMixtureDistribution,
        "fitter": PoissonMixtureFitter,
        "simulator": PoissonMixtureSimulator,
        "computer": PoissonMixtureComputer,
    },
    "HurdlePoisson": {
        "distribution": HurdlePoissonDistribution,
        "fitter": HurdlePoissonFitter,
        "simulator": HurdlePoissonSimulator,
        "computer": HurdlePoissonComputer,
    },
    "HurdlePoissonGamma": {
        "distribution": HurdlePoissonGammaDistribution,
        "fitter": HurdlePoissonGammaFitter,
        "simulator": HurdlePoissonGammaSimulator,
        "computer": HurdlePoissonGammaComputer,
    },
}

# Auto-built reverse lookup
DISTRIBUTION_TO_MODEL = {
    entry["distribution"]: name
    for name, entry in MODEL_REGISTRY.items()
}
