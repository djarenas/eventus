"""
arrays_violin_config.py

ArraysViolinConfig — configuration for ArraysViolinPlotter.

The plotter receives a pre-built {key: np.ndarray} dict and draws one
violin per key. This config controls all visual aspects of that plot.

Plot order is determined by the order categories are defined — in code
or in YAML. First defined = leftmost violin.

Section dataclasses:
    ViolinAxisConfig   — tick control + y_min / y_max  (violin_style_config.py)
    ViolinStyleConfig  — bandwidth, box, points         (violin_style_config.py)
    PercentilesConfig  — reference lines                (percentiles_config.py)
    CategoryConfig     — per-key color + label          (category_config.py)

Inherited from BasePlotConfig:
    canvas: CanvasConfig  — figsize, dpi, font_size
    build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
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
)
from eventus.visualizers.configs.violin_style_config import (
    ViolinAxisConfig,
    ViolinStyleConfig,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "ArraysViolinConfig"


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class ArraysViolinConfig(BasePlotConfig):
    """
    Full configuration for ArraysViolinPlotter.

    categories keys must match the keys in the arrays dict passed to
    the plotter. Order of categories = left-to-right plot order.

    Example (minimal):
        config = ArraysViolinConfig()

    Example (from YAML):
        config = ArraysViolinConfig.build_from_yaml("my_config.yaml")

    Example (from dict):
        config = ArraysViolinConfig.build_from_dict({
            "canvas": {"figsize": [12, 7]},
            "labels": {"title": "Duration by hospital", "units": "days"},
            "categories": {
                "all_data":   {"color": "#AAAAAA", "label": "All"},
                "Hospital_A": {"color": "#028090", "label": "North"},
                "Hospital_B": {"color": "#E05C40", "label": "South"},
            },
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    labels:      AxisLabels                = field(default_factory=AxisLabels)
    axes:        ViolinAxisConfig          = field(default_factory=ViolinAxisConfig)
    style:       ViolinStyleConfig         = field(default_factory=ViolinStyleConfig)
    percentiles: PercentilesConfig         = field(default_factory=PercentilesConfig)
    categories:  dict[str, CategoryConfig] = field(default_factory=dict)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {
        "labels", "axes", "style", "percentiles", "categories",
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.categories, dict):
            raise err(self._PREFIX, f"categories must be a dict, got {type(self.categories).__name__}")
        if len(self.categories) > self.style.max_categories:
            raise err(
                self._PREFIX,
                f"categories has {len(self.categories)} entries but "
                f"style.max_categories={self.style.max_categories}. "
                f"Increase max_categories or reduce categories.",
            )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def plot_order(self) -> list[str]:
        """Left-to-right violin order — matches definition order in categories."""
        return list(self.categories.keys())

    def resolve(self, array_keys: list[str]) -> dict[str, CategoryConfig]:
        """
        Return a CategoryConfig for every key in array_keys.
        Configured entries take priority; missing ones are auto-assigned
        from the default palette with a warning.
        """
        resolved: dict[str, CategoryConfig] = {}
        auto_idx = 0
        for key in array_keys:
            if key in self.categories:
                resolved[key] = self.categories[key]
            else:
                color = _DEFAULT_PALETTE[auto_idx % len(_DEFAULT_PALETTE)]
                warnings.warn(
                    f"[{_PREFIX}] No CategoryConfig for {key!r} "
                    f"— auto-assigning color {color}",
                    UserWarning, stacklevel=2,
                )
                resolved[key] = CategoryConfig(color=color)
                auto_idx += 1
        return resolved

    # ── Build ─────────────────────────────────────────────────────────────────

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "ArraysViolinConfig":
        return cls(
            canvas      = canvas,
            labels      = build_section(AxisLabels,       data.get("labels"),      _PREFIX),
            axes        = build_section(ViolinAxisConfig, data.get("axes"),        _PREFIX),
            style       = build_section(ViolinStyleConfig, data.get("style"),      _PREFIX),
            percentiles = build_section(PercentilesConfig, data.get("percentiles"), _PREFIX),
            categories  = parse_categories(data.get("categories")),
        )

    def __repr__(self) -> str:
        return (
            f"ArraysViolinConfig(\n"
            f"  canvas      : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  labels      : title={self.labels.title!r}, units={self.labels.units!r}\n"
            f"  axes        : y_min={self.axes.y_min}, y_max={self.axes.y_max}\n"
            f"  style       : bandwidth={self.style.bandwidth!r}, show_box={self.style.show_box}\n"
            f"  percentiles : show={self.percentiles.show}, values={self.percentiles.values}\n"
            f"  categories  : {self.plot_order}\n"
            f")"
        )
