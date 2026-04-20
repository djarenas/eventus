"""
base_violin_config.py
BaseViolinConfig — shared foundation for all eventus violin plot configs.

Contains all shared nested dataclasses (CategoryConfig, StyleConfig,
PercentilesConfig, LabelsConfig) and the base config class with shared
build/save logic.

Subclasses:
    EventDurationViolinConfig  — stratify by data category values
    IntermediateViolinConfig   — stratify by intermediate metric columns
"""
from __future__ import annotations
from dataclasses import dataclass, field
import yaml

_ERROR_PREFIX = "[BaseViolinConfig] Error"

_VALID_BW             = {"scott", "silverman"}
_VALID_LS             = {"dashed", "dotted", "solid"}
_VALID_DURATION_UNITS = {"days", "months", "years"}
_DURATION_DIVISORS    = {"days": 1.0, "months": 30.44, "years": 365.25}


# ── Nested config dataclasses ─────────────────────────────────────────────

@dataclass
class CategoryConfig:
    """
    Config for one category — color and optional display label.

    Parameters
    ----------
    color : str
        7-character hex color e.g. '#028090'.
    label : str | None
        Display label for x-axis tick. Falls back to raw category
        value if None.
    """
    color: str
    label: str | None = None

    def __post_init__(self) -> None:
        if not (isinstance(self.color, str) and
                self.color.startswith("#") and
                len(self.color) == 7):
            raise ValueError(
                f"[CategoryConfig] Error: color must be a 7-character hex "
                f"color like '#028090', got {self.color!r}"
            )


@dataclass
class StyleConfig:
    """Controls overall visual appearance."""
    figsize:        list        = field(default_factory=lambda: [10, 6])
    dpi:            int         = 150
    bandwidth:      str         = "scott"
    show_box:       bool        = True
    show_points:    bool        = False
    point_alpha:    float       = 0.3
    point_size:     float       = 3.0
    max_categories: int         = 4
    y_min:          float | None = None
    y_max:          float | None = None

    def __post_init__(self) -> None:
        if self.bandwidth not in _VALID_BW:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.bandwidth must be one of "
                f"{sorted(_VALID_BW)}, got {self.bandwidth!r}"
            )
        if not (0.0 <= self.point_alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: style.point_alpha must be between "
                f"0 and 1, got {self.point_alpha}"
            )
        if self.point_size <= 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.point_size must be > 0, "
                f"got {self.point_size}"
            )
        if self.dpi <= 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.dpi must be > 0, got {self.dpi}"
            )
        if len(self.figsize) != 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.figsize must be [width, height], "
                f"got {self.figsize}"
            )
        if self.max_categories < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.max_categories must be >= 1, "
                f"got {self.max_categories}"
            )
        if self.y_min is not None and self.y_max is not None:
            if self.y_min >= self.y_max:
                raise ValueError(
                    f"{_ERROR_PREFIX}: style.y_min ({self.y_min}) must be "
                    f"less than style.y_max ({self.y_max})"
                )


@dataclass
class PercentilesConfig:
    """Controls percentile reference lines drawn across each violin."""
    show:        bool  = True
    values:      list  = field(default_factory=lambda: [25, 50, 75, 90])
    color:       str   = "#333333"
    linestyle:   str   = "dashed"
    show_labels: bool  = True

    def __post_init__(self) -> None:
        if self.linestyle not in _VALID_LS:
            raise ValueError(
                f"{_ERROR_PREFIX}: percentiles.linestyle must be one of "
                f"{sorted(_VALID_LS)}, got {self.linestyle!r}"
            )
        bad = [v for v in self.values if not (0 <= v <= 100)]
        if bad:
            raise ValueError(
                f"{_ERROR_PREFIX}: percentiles.values must be between "
                f"0 and 100, got {bad}"
            )


@dataclass
class LabelsConfig:
    """
    Controls text labels on the plot.

    duration_unit controls both the y-axis scale and the auto-filled
    ylabel. Set to 'days' (default), 'months', or 'years'.
    If ylabel is explicitly set it is used as-is regardless of unit.
    """
    title:         str | None = None
    xlabel:        str | None = None
    ylabel:        str | None = None   # auto-fills from duration_unit if None
    duration_unit: str        = "days"

    def __post_init__(self) -> None:
        if self.duration_unit not in _VALID_DURATION_UNITS:
            raise ValueError(
                f"{_ERROR_PREFIX}: labels.duration_unit must be one of "
                f"{sorted(_VALID_DURATION_UNITS)}, "
                f"got {self.duration_unit!r}"
            )

    @property
    def resolved_ylabel(self) -> str:
        """Return ylabel — explicit value or auto-filled from duration_unit."""
        if self.ylabel is not None:
            return self.ylabel
        return f"Duration ({self.duration_unit})"

    @property
    def divisor(self) -> float:
        """Return the divisor to convert days to the configured unit."""
        return _DURATION_DIVISORS[self.duration_unit]


# ── Base config class ─────────────────────────────────────────────────────

class BaseViolinConfig:
    """
    Shared foundation for eventus violin plot configs.

    Holds all shared nested config objects and provides shared
    build/save logic. Not intended to be instantiated directly —
    use EventDurationViolinConfig or IntermediateViolinConfig instead.

    Subclasses must define _VALID_SECTIONS as a class attribute
    listing their allowed top-level YAML sections.

    Attributes
    ----------
    stratify : dict[str, CategoryConfig]
        Maps category keys to CategoryConfig objects.
    style : StyleConfig
    percentiles : PercentilesConfig
    labels : LabelsConfig
    """

    # Subclasses override to add their own sections
    _VALID_SECTIONS: set[str] = {"stratify", "style", "percentiles", "labels"}

    def __init__(
        self,
        stratify:    dict            = None,
        style:       StyleConfig     = None,
        percentiles: PercentilesConfig = None,
        labels:      LabelsConfig    = None,
    ) -> None:
        self.stratify    = stratify    or {}
        self.style       = style       or StyleConfig()
        self.percentiles = percentiles or PercentilesConfig()
        self.labels      = labels      or LabelsConfig()

    # ------------------------------------------------------------------ #
    # Shared properties
    # ------------------------------------------------------------------ #

    @property
    def category_keys(self) -> list[str]:
        """All keys in stratify in definition order."""
        return list(self.stratify.keys())

    # ------------------------------------------------------------------ #
    # Shared classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def _parse_yaml(cls, path: str) -> dict:
        """Load and validate top-level YAML sections."""
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
                f"got {type(raw).__name__}"
            )
        unknown = set(raw.keys()) - cls._VALID_SECTIONS
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown sections in YAML: {sorted(unknown)}. "
                f"Valid sections: {sorted(cls._VALID_SECTIONS)}"
            )
        return raw

    @staticmethod
    def _build_nested(cls_, data: dict | None):
        """Build a nested dataclass from a dict, raising on unknown keys."""
        if data is None:
            return cls_()
        valid   = set(cls_.__dataclass_fields__.keys())
        unknown = set(data.keys()) - valid
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown keys in "
                f"'{cls_.__name__}': {sorted(unknown)}"
            )
        return cls_(**data)

    @staticmethod
    def _parse_stratify(raw_stratify: dict | None) -> dict[str, CategoryConfig]:
        """Parse the stratify section into {key: CategoryConfig}."""
        stratify = {}
        for key, val in (raw_stratify or {}).items():
            if not isinstance(val, dict):
                raise ValueError(
                    f"{_ERROR_PREFIX}: stratify.{key!r} must be a mapping "
                    f"with 'color' and optional 'label', "
                    f"got {type(val).__name__}"
                )
            stratify[key] = CategoryConfig(**val)
        return stratify

    # ------------------------------------------------------------------ #
    # Shared save logic
    # ------------------------------------------------------------------ #

    def _stratify_to_dict(self) -> dict:
        """Serialize stratify section to a plain dict for YAML."""
        out = {}
        for key, cat in self.stratify.items():
            entry = {"color": cat.color}
            if cat.label is not None:
                entry["label"] = cat.label
            out[key] = entry
        return out

    def _base_yaml_dict(self) -> dict:
        """Build the shared sections of the YAML dict."""
        return {
            "stratify": self._stratify_to_dict(),
            "style": {
                "figsize":        self.style.figsize,
                "dpi":            self.style.dpi,
                "bandwidth":      self.style.bandwidth,
                "show_box":       self.style.show_box,
                "show_points":    self.style.show_points,
                "point_alpha":    self.style.point_alpha,
                "point_size":     self.style.point_size,
                "max_categories": self.style.max_categories,
                "y_min":          self.style.y_min,
                "y_max":          self.style.y_max,
            },
            "percentiles": {
                "show":        self.percentiles.show,
                "values":      self.percentiles.values,
                "color":       self.percentiles.color,
                "linestyle":   self.percentiles.linestyle,
                "show_labels": self.percentiles.show_labels,
            },
            "labels": {
                "title":         self.labels.title,
                "xlabel":        self.labels.xlabel,
                "ylabel":        self.labels.ylabel,
                "duration_unit": self.labels.duration_unit,
            },
        }

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file. Subclasses may extend."""
        cfg = self._base_yaml_dict()
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(\n"
            f"  stratify    : {self.category_keys}\n"
            f"  show_box    : {self.style.show_box}\n"
            f"  show_points : {self.style.show_points}\n"
            f"  percentiles : {self.percentiles.values}\n"
            f"  unit        : {self.labels.duration_unit}\n"
            f")"
        )
