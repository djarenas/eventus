"""
violin_config.py

Shared violin plot configuration classes and EventDurationViolinConfig.

Section dataclasses (all validated on construction):
    ViolinAxisConfig    — x/y tick control + y_min / y_max bounds
    ViolinStyleConfig   — bandwidth, box, point, and category display settings

Base config:
    BaseViolinConfig    — canvas, stratify, labels, axes, style, percentiles
                          Base class for all violin configs; not instantiated directly.

Concrete config:
    EventDurationViolinConfig — adds stratify_by column name

Imported from shared modules:
    AxisLabels          — title, subtitle, xlabel, ylabel, units (base_plot_config.py)
    PercentilesConfig   — percentile reference lines              (percentiles_config.py)
    CategoryConfig      — per-category color + label             (category_config.py)
    parse_categories    — dict parser for CategoryConfig entries  (category_config.py)

Inherited from BasePlotConfig:
    canvas: CanvasConfig  — figsize, dpi, font_size
    build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
    AxisConfig,
    AxisLabels,
    BasePlotConfig,
    CanvasConfig,
)
from eventus.visualizers.configs.category_config import CategoryConfig, parse_categories
from eventus.visualizers.configs.percentiles_config import PercentilesConfig
from eventus.visualizers.configs.plot_config_utils import (
    _DEFAULT_PALETTE,
    build_section,
    err,
    validate_alpha,
    validate_choice,
    validate_float,
    validate_positive_float,
    validate_positive_integer,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX        = "ViolinConfig"
_VALID_BW      = {"scott", "silverman"}


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class ViolinAxisConfig(AxisConfig):
    """
    Axis configuration for violin plots.
    Extends AxisConfig with optional y-axis bounds.
    """
    # --- Inherited from AxisConfig ---
    # x_ticks:         list[float] | None
    # y_ticks:         list[float] | None
    # x_tick_rotation: float
    # y_tick_rotation: float
    # x_tick_format:   str | None
    # y_tick_format:   str | None
    # tick_font_size:  int | None

    y_min: float | None = None
    y_max: float | None = None

    _PREFIX: ClassVar[str] = "ViolinAxisConfig"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.y_min is not None:
            self.y_min = validate_float(self.y_min, self._PREFIX, "y_min")
        if self.y_max is not None:
            self.y_max = validate_float(self.y_max, self._PREFIX, "y_max")
        if self.y_min is not None and self.y_max is not None:
            if self.y_min >= self.y_max:
                raise err(
                    self._PREFIX,
                    f"y_min ({self.y_min}) must be less than y_max ({self.y_max})",
                )


@dataclass
class ViolinStyleConfig:
    """Visual style for violin plots."""
    bandwidth:      str   = "scott"
    show_box:       bool  = True
    show_points:    bool  = False
    point_alpha:    float = 0.3
    point_size:     float = 3.0
    max_categories: int   = 4

    _PREFIX: ClassVar[str] = "ViolinStyleConfig"

    def __post_init__(self) -> None:
        validate_choice(self.bandwidth, _VALID_BW, "style.bandwidth", self._PREFIX)
        self.point_alpha = validate_alpha(self.point_alpha,       self._PREFIX, "point_alpha")
        self.point_size  = validate_positive_float(self.point_size,  self._PREFIX, "point_size")
        self.max_categories = validate_positive_integer(self.max_categories, self._PREFIX, "max_categories")
        if self.max_categories < 1:
            raise err(self._PREFIX, f"style.max_categories must be >= 1, got {self.max_categories}")


# ── Base violin config ────────────────────────────────────────────────────────

@dataclass
class BaseViolinConfig(BasePlotConfig):
    """
    Shared base for all violin plot configs.
    Not intended to be instantiated directly.

    Subclasses must implement _build_sections().
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    stratify:    dict[str, CategoryConfig] = field(default_factory=dict)
    labels:      AxisLabels                = field(default_factory=AxisLabels)
    axes:        ViolinAxisConfig          = field(default_factory=ViolinAxisConfig)
    style:       ViolinStyleConfig         = field(default_factory=ViolinStyleConfig)
    percentiles: PercentilesConfig         = field(default_factory=PercentilesConfig)

    _PREFIX:   ClassVar[str]      = "BaseViolinConfig"
    _SECTIONS: ClassVar[set[str]] = {
        "stratify", "labels", "axes", "style", "percentiles",
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.stratify, dict):
            raise err(self._PREFIX, f"stratify must be a dict, got {type(self.stratify).__name__}")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def category_keys(self) -> list[str]:
        """All keys in stratify in definition order."""
        return list(self.stratify.keys())

    @property
    def plot_order(self) -> list[str]:
        """Full plot order — all_data first if present, then remaining keys."""
        keys = self.category_keys
        if "all_data" in keys:
            return ["all_data"] + [k for k in keys if k != "all_data"]
        return keys

    def resolve_colors(self, category_keys: list) -> dict[str, CategoryConfig]:
        """
        Return a CategoryConfig for every key.
        Configured entries take priority; missing ones are auto-assigned
        from the default palette with a warning.
        """
        resolved: dict[str, CategoryConfig] = {}
        auto_idx = 0
        ordered = list(self.stratify) + [k for k in category_keys if k not in self.stratify]
        for key in ordered:
            if key in self.stratify:
                resolved[key] = self.stratify[key]
            else:
                color = _DEFAULT_PALETTE[auto_idx % len(_DEFAULT_PALETTE)]
                warnings.warn(
                    f"[{self._PREFIX}] No CategoryConfig for {key!r} "
                    f"— auto-assigning color {color}",
                    UserWarning, stacklevel=2,
                )
                resolved[key] = CategoryConfig(color=color)
                auto_idx += 1
        return resolved

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "BaseViolinConfig":
        return cls(
            canvas      = canvas,
            stratify    = parse_categories(data.get("stratify")),
            labels      = build_section(AxisLabels,       data.get("labels"),      cls._PREFIX),
            axes        = build_section(ViolinAxisConfig, data.get("axes"),        cls._PREFIX),
            style       = build_section(ViolinStyleConfig, data.get("style"),      cls._PREFIX),
            percentiles = build_section(PercentilesConfig, data.get("percentiles"), cls._PREFIX),
        )


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class EventDurationViolinConfig(BaseViolinConfig):
    """
    Full configuration for EventsDurationViolinPlotter.

    stratify_by names the column in events.data to group by.
    Category keys in stratify are the raw values found in that column.
    The reserved key 'all_data' always plots first if present.

    Example (minimal):
        config = EventDurationViolinConfig()

    Example (from YAML):
        config = EventDurationViolinConfig.build_from_yaml("my_config.yaml")

    Example (from dict):
        config = EventDurationViolinConfig.build_from_dict({
            "canvas":      {"figsize": [10, 6]},
            "stratify_by": "hospital_id",
            "stratify": {
                "all_data": {"color": "#AAAAAA", "label": "All patients"},
                "H01":      {"color": "#028090", "label": "Hospital North"},
            },
        })
    """
    # --- Inherited from BaseViolinConfig / BasePlotConfig ---
    # canvas:      CanvasConfig
    # stratify:    dict[str, CategoryConfig]
    # labels:      AxisLabels
    # axes:        ViolinAxisConfig
    # style:       ViolinStyleConfig
    # percentiles: PercentilesConfig

    stratify_by: str | None = None

    _PREFIX:   ClassVar[str]      = "EventDurationViolinConfig"
    _SECTIONS: ClassVar[set[str]] = {
        "stratify_by", "stratify", "labels", "axes", "style", "percentiles",
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.stratify_by is not None and (
            not isinstance(self.stratify_by, str) or not self.stratify_by.strip()
        ):
            raise err(
                self._PREFIX,
                f"stratify_by must be a non-empty string or None, got {self.stratify_by!r}",
            )
        non_total = self.category_keys_non_total
        if len(non_total) > self.style.max_categories:
            raise err(
                self._PREFIX,
                f"stratify has {len(non_total)} categories but "
                f"style.max_categories={self.style.max_categories}. "
                f"Categories: {non_total}. "
                f"Increase max_categories or reduce categories.",
            )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def has_total(self) -> bool:
        """True if all_data is configured."""
        return "all_data" in self.stratify

    @property
    def category_keys_non_total(self) -> list[str]:
        """Category keys excluding all_data, in config order."""
        return [k for k in self.stratify if k != "all_data"]

    # ── Build ─────────────────────────────────────────────────────────────────

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "EventDurationViolinConfig":
        return cls(
            canvas       = canvas,
            stratify_by  = data.get("stratify_by"),
            stratify     = parse_categories(data.get("stratify")),
            labels       = build_section(AxisLabels,        data.get("labels"),      _PREFIX),
            axes         = build_section(ViolinAxisConfig,  data.get("axes"),        _PREFIX),
            style        = build_section(ViolinStyleConfig, data.get("style"),       _PREFIX),
            percentiles  = build_section(PercentilesConfig, data.get("percentiles"), _PREFIX),
        )

    def __repr__(self) -> str:
        return (
            f"EventDurationViolinConfig(\n"
            f"  canvas       : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  stratify_by  : {self.stratify_by!r}\n"
            f"  stratify     : {self.category_keys}\n"
            f"  style        : bandwidth={self.style.bandwidth!r}, show_box={self.style.show_box}\n"
            f"  percentiles  : show={self.percentiles.show}, values={self.percentiles.values}\n"
            f"  axes         : y_min={self.axes.y_min}, y_max={self.axes.y_max}\n"
            f"  labels       : units={self.labels.units!r}\n"
            f")"
        )
