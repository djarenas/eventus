"""
event_duration_violin_config.py
EventDurationViolinConfig — violin plot config for EventsDurationViolinPlotter.

Stratify keys are raw category values from events.data
e.g. hospital IDs, DRG codes, or any other categorical column.

The reserved key 'all_data' configures the total violin — if present,
it is always plotted first.

stratify_by names the column in events.data to group by. It lives
in the config — not the plotter constructor — so the choice is
versioned and documented alongside all other analytical decisions.
"""
from __future__ import annotations

from .base_violin_config import (
    BaseViolinConfig,
    CategoryConfig,
    StyleConfig,
    PercentilesConfig,
    LabelsConfig,
)

_ERROR_PREFIX  = "[EventDurationViolinConfig] Error"


class EventDurationViolinConfig(BaseViolinConfig):
    """
    Violin plot configuration for EventsDurationViolinPlotter.

    stratify_by names the column in events.data to group by.
    Stratify keys are the raw category values found in that column —
    e.g. hospital IDs, DRG codes, or any categorical column.

    The reserved key 'all_data' configures the total violin.
    If present it is always plotted first. If absent no total
    violin is drawn.

    Raises at construction if:
    - stratify_by is missing or not a string
    - More non-total categories than style.max_categories

    Examples
    --------
    >>> config = EventDurationViolinConfig.build_from_yaml("violin_config.yaml")
    >>> config = EventDurationViolinConfig.build_with_defaults("hospital_id")
    >>> config.to_yaml("my_violin_config.yaml")

    Example YAML
    ------------
    stratify_by: hospital_id

    stratify:
      all_data:
        color: "#AAAAAA"
        label: "All patients"
      H01:
        color: "#028090"
        label: "Hospital North"
      H02:
        color: "#E05C40"
        label: "Hospital South"

    style:
      figsize:        [10, 6]
      dpi:            150
      bandwidth:      scott
      show_box:       true
      show_points:    false
      point_alpha:    0.3
      point_size:     3.0
      max_categories: 4

    percentiles:
      show:        true
      values:      [25, 50, 75, 90]
      linestyle:   dashed
      show_labels: true

    labels:
      ylabel:        null
      duration_unit: days
    """

    _VALID_SECTIONS = {"stratify_by", "stratify", "style", "percentiles", "labels"}

    def __init__(
        self,
        stratify_by: str | None        = None,
        stratify:    dict              = None,
        style:       StyleConfig       = None,
        percentiles: PercentilesConfig = None,
        labels:      LabelsConfig      = None,
    ) -> None:
        super().__init__(
            stratify    = stratify,
            style       = style,
            percentiles = percentiles,
            labels      = labels,
        )
        if stratify_by is not None and (
            not isinstance(stratify_by, str) or not stratify_by.strip()
        ):
            raise ValueError(
                f"{_ERROR_PREFIX}: stratify_by must be a non-empty string or None, "
                f"got {stratify_by!r}"
            )
        self.stratify_by = stratify_by
        self._validate()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate(self) -> None:
        # Max categories check — always invalid regardless of context
        non_total = self.category_keys_non_total
        if len(non_total) > self.style.max_categories:
            raise ValueError(
                f"{_ERROR_PREFIX}: stratify has {len(non_total)} categories "
                f"but style.max_categories={self.style.max_categories}. "
                f"Categories: {non_total}. "
                f"Increase max_categories or reduce categories."
            )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def has_total(self) -> bool:
        """True if all_data is configured."""
        return "all_data" in self.stratify

    @property
    def category_keys_non_total(self) -> list[str]:
        """Category keys excluding all_data, in config order."""
        return [k for k in self.stratify if k != "all_data"]

    @property
    def plot_order(self) -> list[str]:
        """Full plot order — all_data first if present, then categories."""
        return (
            ["all_data"] if self.has_total else []
        ) + self.category_keys_non_total

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_with_defaults(cls, stratify_by: str | None = None) -> "EventDurationViolinConfig":
        """
        Return a config with all_data total violin and no stratification.

        Parameters
        ----------
        stratify_by : str | None
            Column in events.data to stratify by. If None, only the
            total violin is drawn.
        """
        return cls(
            stratify_by = stratify_by,
            stratify    = {
                "all_data": CategoryConfig(color="#AAAAAA", label="All")
            },
        )

    @classmethod
    def build_from_yaml(cls, path: str) -> "EventDurationViolinConfig":
        """Build an EventDurationViolinConfig from a YAML file."""
        raw = cls._parse_yaml(path)

        return cls(
            stratify_by = raw.get("stratify_by"),
            stratify    = cls._parse_stratify(raw.get("stratify")),
            style       = cls._build_nested(StyleConfig,       raw.get("style")),
            percentiles = cls._build_nested(PercentilesConfig, raw.get("percentiles")),
            labels      = cls._build_nested(LabelsConfig,      raw.get("labels")),
        )

    # ------------------------------------------------------------------ #
    # Save — extend base to include stratify_by
    # ------------------------------------------------------------------ #

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        import yaml
        cfg = {"stratify_by": self.stratify_by}
        cfg.update(self._base_yaml_dict())
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventDurationViolinConfig(\n"
            f"  stratify_by : {self.stratify_by!r}\n"
            f"  stratify    : {list(self.stratify.keys())}\n"
            f"  show_box    : {self.style.show_box}\n"
            f"  show_points : {self.style.show_points}\n"
            f"  percentiles : {self.percentiles.values}\n"
            f"  unit        : {self.labels.duration_unit}\n"
            f")"
        )
