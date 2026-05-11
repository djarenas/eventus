"""
histogram_plot_config.py

HistogramPlotConfig — full configuration for histogram plots in eventus.

Section dataclasses (all validated on construction):
    HistogramLabels      — title, subtitle, xlabel, ylabel, units
    HistogramStyleConfig — alpha, color, show_grid, edgecolor
    StratificationConfig — overlaid or faceted category breakdown

Imported from shared modules:
    PercentilesConfig    — percentile reference lines  (percentiles_config.py)
    CategoryConfig       — per-category color + label  (category_config.py)

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
    EdgeStyleConfig,
)
from eventus.visualizers.configs.bins_config import BinsConfig
from eventus.visualizers.configs.category_config import CategoryConfig, parse_categories
from eventus.visualizers.configs.percentiles_config import PercentilesConfig
from eventus.visualizers.configs.plot_config_utils import (
    _DEFAULT_PALETTE,
    build_section,
    err,
    validate_choice,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX             = "histogram config"
_VALID_STRAT_STYLES = {"overlay", "facet"}


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class HistogramLabels(AxisLabels):
    """Text labels for histogram plots."""
    # --- Inherited from AxisLabels / BasePlotLabels ---
    # title:    str | None
    # subtitle: str | None
    # xlabel:   str | None
    # ylabel:   str | None
    # units:    str | None

    pass   # no histogram-specific label fields yet


@dataclass
class HistogramStyleConfig(EdgeStyleConfig):
    """Visual style for histogram plots."""
    # --- Inherited from EdgeStyleConfig / AxisStyleConfig / BaseStyleConfig ---
    # alpha:     float
    # color:     str
    # show_grid: bool
    # edgecolor: str

    _PREFIX: ClassVar[str] = "histogram style"

    # no histogram-specific style fields yet


@dataclass
class StratificationConfig:
    """
    Controls stratified histogram rendering.
    Only used when a stratify_by column is passed to the plotter.
    """
    style:          str                       = "overlay"
    max_categories: int                       = 10
    categories:     dict[str, CategoryConfig] = field(default_factory=dict)

    _PREFIX: ClassVar[str] = "histogram stratification"

    def __post_init__(self) -> None:
        validate_choice(
            self.style, _VALID_STRAT_STYLES,
            "stratification.style", self._PREFIX,
        )
        if self.max_categories < 2:
            raise err(
                self._PREFIX,
                f"stratification.max_categories must be >= 2, "
                f"got {self.max_categories}",
            )

    def resolve(self, category_keys: list) -> dict[str, CategoryConfig]:
        """
        Return a CategoryConfig for every category key.
        User-supplied entries take priority; missing ones are auto-assigned
        from the default palette with a warning.
        """
        resolved: dict[str, CategoryConfig] = {}
        auto_idx = 0
        ordered = list(self.categories) + [
            k for k in category_keys if k not in self.categories
        ]
        for key in ordered:
            if key in self.categories:
                resolved[key] = self.categories[key]
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


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class HistogramPlotConfig(BasePlotConfig):
    """
    Full configuration for histogram plots.

    Example (minimal):
        config = HistogramPlotConfig()

    Example (from YAML):
        config = HistogramPlotConfig.build_from_yaml("my_config.yaml")

    Example (from dict):
        config = HistogramPlotConfig.build_from_dict({
            "canvas": {"figsize": [10, 5]},
            "bins":   {"type": "uniform", "n_bins": 10, "min": 0, "max": 365},
            "style":  {"color": "#E05C40"},
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    bins:             BinsConfig             = field(default_factory=BinsConfig.auto)
    labels:           HistogramLabels        = field(default_factory=HistogramLabels)
    axes:             AxisConfig             = field(default_factory=AxisConfig)
    style:            HistogramStyleConfig   = field(default_factory=HistogramStyleConfig)
    percentile_lines: PercentilesConfig      = field(default_factory=PercentilesConfig)
    stratification:   StratificationConfig   = field(default_factory=StratificationConfig)

    _PREFIX:   ClassVar[str]      = "histogram config"
    _SECTIONS: ClassVar[set[str]] = {
        "bins", "labels", "axes", "style", "percentile_lines", "stratification",
    }

    def __post_init__(self) -> None:
        super().__post_init__()

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "HistogramPlotConfig":
        # stratification.categories needs parse_categories, not plain build_section
        strat_data = data.get("stratification") or {}
        stratification = StratificationConfig(
            style          = strat_data.get("style",          "overlay"),
            max_categories = strat_data.get("max_categories", 10),
            categories     = parse_categories(strat_data.get("categories")),
        )
        return cls(
            canvas           = canvas,
            bins             = BinsConfig.from_dict(data.get("bins")),
            labels           = build_section(HistogramLabels,      data.get("labels"),          _PREFIX),
            axes             = build_section(AxisConfig,           data.get("axes"),             _PREFIX),
            style            = build_section(HistogramStyleConfig, data.get("style"),            _PREFIX),
            percentile_lines = build_section(PercentilesConfig,    data.get("percentile_lines"), _PREFIX),
            stratification   = stratification,
        )

    def __repr__(self) -> str:
        return (
            f"HistogramPlotConfig(\n"
            f"  canvas           : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  bins             : {self.bins.type}\n"
            f"  style            : color={self.style.color}, alpha={self.style.alpha}\n"
            f"  percentile_lines : show={self.percentile_lines.show}, values={self.percentile_lines.values}\n"
            f"  stratification   : style='{self.stratification.style}', max_categories={self.stratification.max_categories}\n"
            f")"
        )
