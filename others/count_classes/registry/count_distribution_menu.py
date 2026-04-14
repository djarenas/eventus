"""Count distribution menu.

A menu defines which models are in play for a study. It knows
the full mapping from model name to distribution, fitter,
simulator, and computer classes. It can be built from a YAML
file or a list of names, and can generate permutations of
itself for exhaustive comparison studies.

The master registry of all known models lives here as a
module-level constant.
"""
import yaml
from dataclasses import dataclass, field
from itertools import combinations
import numpy as np
import pandas as pd

from .model_registry import MODEL_REGISTRY
from .count_distributions import CountDistribution

# =====================================================================
#  CountModelEntry
# =====================================================================

@dataclass
class CountModelEntry:
    """One model's full set of classes and optional configuration.

    Represents everything needed to work with a single count model:
    its distribution, fitter, simulator, and computer classes, plus
    any model-specific configuration (e.g., k for PoissonMixture).

    Attributes:
        name (str): Short model name (e.g., "Poisson").
        distribution_class (type): The distribution class.
        fitter_class (type): The fitter class.
        simulator_class (type): The simulator class.
        computer_class (type): The computer class.
        config (dict): Optional model-specific configuration
            passed to the fitter (e.g., {"k": 3}).
    """

    _ERROR_PREFIX = "[CountModelEntry]"

    name: str
    distribution_class: type
    fitter_class: type
    simulator_class: type
    computer_class: type
    config: dict = field(default_factory=dict)

    @classmethod
    def build_from_name(cls, name: str, config: dict = None) -> "CountModelEntry":
        """Build an entry by looking up a name in the master registry.

        Args:
            name: Model name (e.g., "Poisson", "PoissonGamma").
            config: Optional model-specific configuration.

        Returns:
            A fully populated CountModelEntry.

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is not in MODEL_REGISTRY.
        """
        if not isinstance(name, str):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_name: "
                f"name must be a string, got {type(name).__name__}"
            )

        if name not in MODEL_REGISTRY:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_name: "
                f"Unknown model '{name}'. "
                f"Available models: {list(MODEL_REGISTRY.keys())}"
            )

        if config is not None and not isinstance(config, dict):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_name: "
                f"config must be a dict or None, got {type(config).__name__}"
            )

        reg = MODEL_REGISTRY[name]
        return cls(
            name=name,
            distribution_class=reg["distribution"],
            fitter_class=reg["fitter"],
            simulator_class=reg["simulator"],
            computer_class=reg["computer"],
            config=config or {},
        )

    def __repr__(self) -> str:
        config_str = f", config={self.config}" if self.config else ""
        return f"CountModelEntry({self.name}{config_str})"


# =====================================================================
#  CountDistributionMenu
# =====================================================================

class CountDistributionMenu:
    """A validated set of models to work with.

    The menu defines which models are in play for fitting,
    simulation, or comparison studies. It can be built from a
    YAML file or a list of names, and can generate permutations
    of itself for exhaustive studies.

    Attributes:
        entries (list[CountModelEntry]): The models in this menu.

    Example:
        >>> menu = CountDistributionMenu.build_from_names(
        ...     ["Poisson", "PoissonGamma", "ZIP"]
        ... )
        >>> for entry in menu:
        ...     print(entry.name)

    Example (from YAML):
        >>> menu = CountDistributionMenu.build_from_yaml("models.yaml")

    Example (permutations):
        >>> for sub_menu in menu.generate_permutations(min_size=3):
        ...     print([e.name for e in sub_menu])
    """

    _ERROR_PREFIX = "[CountDistributionMenu]"

    # Attribute Declarations
    entries: list

    def __init__(self, entries: list):
        """Create a menu from a list of CountModelEntry objects.

        Args:
            entries: List of CountModelEntry instances.

        Raises:
            TypeError: If entries is not a list or contains non-entries.
            ValueError: If entries is empty or has duplicate names.
        """
        self._validate_entries(entries)
        self.entries = entries

    @classmethod
    def build_from_names(cls, names: list, configs: dict = None) -> "CountDistributionMenu":
        """Build a menu from a list of model names.

        Args:
            names: List of model names (e.g., ["Poisson", "PoissonGamma"]).
            configs: Optional dict mapping model names to config dicts.
                e.g., {"PoissonMixture": {"k": 3}}

        Returns:
            A validated CountDistributionMenu.

        Raises:
            TypeError: If names is not a list.
            ValueError: If names is empty or any name is unknown.
        """
        if not isinstance(names, list):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_names: "
                f"names must be a list, got {type(names).__name__}"
            )
        if len(names) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} build_from_names: "
                f"names list cannot be empty"
            )
        if configs is not None and not isinstance(configs, dict):
            raise TypeError(
                f"{cls._ERROR_PREFIX} build_from_names: "
                f"configs must be a dict or None, got {type(configs).__name__}"
            )

        configs = configs or {}
        entries = []
        for name in names:
            config = configs.get(name, {})
            entry = CountModelEntry.build_from_name(name, config)
            entries.append(entry)
        return cls(entries)

    @classmethod
    def build_from_yaml(cls, path: str) -> "CountDistributionMenu":
        """Build a menu from a YAML configuration file.

        Expected YAML format:
            models:
              - name: Poisson
              - name: PoissonGamma
              - name: PoissonMixture
                config:
                  k: 3

        Args:
            path: Path to the YAML file.

        Returns:
            A validated CountDistributionMenu.

        Raises:
            TypeError: If path is not a string.
            FileNotFoundError: If the file does not exist.
            ValueError: If YAML is malformed or contains unknown models.
        """
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
        except Exception as e:
            raise RuntimeError(
                f"{cls._ERROR_PREFIX} build_from_yaml: "
                f"Unexpected error reading '{path}': {e}"
            )

        cls._validate_yaml(config, path)

        entries = []
        for i, item in enumerate(config["models"]):
            if isinstance(item, str):
                entry = CountModelEntry.build_from_name(item)
            elif isinstance(item, dict):
                if "name" not in item:
                    raise ValueError(
                        f"{cls._ERROR_PREFIX} build_from_yaml: "
                        f"Entry {i} in '{path}' is a dict but missing 'name' key. "
                        f"Got keys: {list(item.keys())}"
                    )
                name = item["name"]
                model_config = item.get("config", {})
                entry = CountModelEntry.build_from_name(name, model_config)
            else:
                raise TypeError(
                    f"{cls._ERROR_PREFIX} build_from_yaml: "
                    f"Entry {i} in '{path}' must be a string or dict, "
                    f"got {type(item).__name__}"
                )
            entries.append(entry)

        return cls(entries)

    @classmethod
    def _validate_yaml(cls, config, path: str) -> None:
        """Validate the YAML structure.

        Raises:
            ValueError: If config is not a dict or missing 'models'.
            TypeError: If models is not a list.
        """
        if not isinstance(config, dict):
            raise ValueError(
                f"{cls._ERROR_PREFIX} _validate_yaml: "
                f"YAML at '{path}' must be a dictionary, "
                f"got {type(config).__name__}"
            )
        if "models" not in config:
            raise ValueError(
                f"{cls._ERROR_PREFIX} _validate_yaml: "
                f"YAML at '{path}' must have a 'models' key. "
                f"Found keys: {list(config.keys())}"
            )
        if not isinstance(config["models"], list):
            raise TypeError(
                f"{cls._ERROR_PREFIX} _validate_yaml: "
                f"'models' in '{path}' must be a list, "
                f"got {type(config['models']).__name__}"
            )
        if len(config["models"]) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} _validate_yaml: "
                f"'models' list in '{path}' cannot be empty"
            )

    @classmethod
    def _validate_entries(cls, entries: list) -> None:
        """Validate the list of entries.

        Raises:
            TypeError: If entries is not a list or contains non-entries.
            ValueError: If empty or has duplicate names.
        """
        if not isinstance(entries, list):
            raise TypeError(
                f"{cls._ERROR_PREFIX} _validate_entries: "
                f"entries must be a list, got {type(entries).__name__}"
            )
        if not entries:
            raise ValueError(
                f"{cls._ERROR_PREFIX} _validate_entries: "
                f"entries list cannot be empty"
            )
        for i, entry in enumerate(entries):
            if not isinstance(entry, CountModelEntry):
                raise TypeError(
                    f"{cls._ERROR_PREFIX} _validate_entries: "
                    f"Entry {i} must be a CountModelEntry, "
                    f"got {type(entry).__name__}"
                )

        names = [e.name for e in entries]
        duplicates = set(n for n in names if names.count(n) > 1)
        if duplicates:
            raise ValueError(
                f"{cls._ERROR_PREFIX} _validate_entries: "
                f"Duplicate model names found: {duplicates}"
            )

    def is_valid_model(self, name: str) -> bool:
        """Check if a model name is in this menu.

        Args:
            name: Model name to check.

        Returns:
            True if the model is in the menu.
        """
        return any(e.name == name for e in self.entries)

    def get_entry(self, name: str) -> CountModelEntry:
        """Look up an entry by model name.

        Args:
            name: Model name.

        Returns:
            The matching CountModelEntry.

        Raises:
            KeyError: If name is not in the menu.
        """
        for entry in self.entries:
            if entry.name == name:
                return entry
        raise KeyError(
            f"{self._ERROR_PREFIX} get_entry: "
            f"'{name}' not in menu. "
            f"Available: {[e.name for e in self.entries]}"
        )

    def get_names(self) -> list:
        """Return list of all model names in the menu.

        Returns:
            List of name strings.
        """
        return [e.name for e in self.entries]


    def fit_all(self, counts: np.ndarray | pd.Series) -> dict[str, CountDistribution]:
        """Fit all models in the menu to the given count data.

        Returns a dictionary (name: distribution). 

        Args:
            counts: pd.Series or array-like of counts.

        Returns:
            List of (name, CountDistribution) tuples.

        Raises:
            TypeError: If counts is not a valid type.
            ValueError: If counts is empty.
            RuntimeError: If a fitter fails, includes model name
                and original error in the message.
        """
        # Check input turn into np.ndarray
        if not isinstance(counts, (pd.Series, list, np.ndarray)):
            raise TypeError(
                f"{self._ERROR_PREFIX} fit_all: "
                f"counts must be pd.Series, list, or np.ndarray, "
                f"got {type(counts).__name__}"
            )
        if isinstance(counts, pd.Series):
            counts = counts.to_numpy()
        if len(counts) == 0:
            raise ValueError(
                f"{self._ERROR_PREFIX} fit_all: "
                f"counts cannot be empty"
            )

        results_dict = {}
        for entry in self.entries:
            try:
                if entry.config:
                    fitter = entry.fitter_class.from_counts(counts, **entry.config)
                else:
                    fitter = entry.fitter_class.from_counts(counts)
                dist = fitter.fit()
                results_dict[entry.name] = dist
            except Exception as e:
                raise RuntimeError(
                    f"{self._ERROR_PREFIX} fit_all: "
                    f"Failed to fit '{entry.name}': {e}"
                ) from e

        return results_dict

    def generate_permutations(self, min_size: int = 2) -> list:
        """Generate all sub-menus of this menu.

        Each permutation is a new CountDistributionMenu containing a
        subset of the entries. Useful for studying how model selection
        changes with different candidate sets.

        Args:
            min_size: Minimum number of models per sub-menu.

        Returns:
            List of CountDistributionMenu objects.

        Raises:
            ValueError: If min_size is less than 1 or greater than
                the number of entries.
        """
        if not isinstance(min_size, int) or min_size < 1:
            raise ValueError(
                f"{self._ERROR_PREFIX} generate_permutations: "
                f"min_size must be a positive integer, got {min_size}"
            )
        if min_size > len(self.entries):
            raise ValueError(
                f"{self._ERROR_PREFIX} generate_permutations: "
                f"min_size ({min_size}) cannot exceed number of "
                f"entries ({len(self.entries)})"
            )

        sub_menus = []
        for size in range(min_size, len(self.entries) + 1):
            for combo in combinations(self.entries, size):
                sub_menus.append(CountDistributionMenu(list(combo)))
        return sub_menus

    # ---- Dunder methods ----

    def __iter__(self):
        """Iterate over entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Number of models in the menu."""
        return len(self.entries)

    def __contains__(self, name: str) -> bool:
        """Check if a model name is in the menu."""
        return self.is_valid_model(name)

    def __repr__(self) -> str:
        names = [e.name for e in self.entries]
        return f"CountDistributionMenu({names})"
