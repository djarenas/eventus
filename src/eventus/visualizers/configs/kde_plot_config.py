"""
kde_plot_config.py
KDEPlotConfig — configuration for KDE density curve plots.

Standalone and reusable — any plotter that needs a KDE curve can use it.

Section dataclasses (all validated on construction):
    KDEStyleConfig  — line color, alpha, fill_alpha, linewidth, bandwidth, show_grid

Inherited from BasePlotConfig:
    canvas: CanvasConfig  — figsize, dpi, font_size
    build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
    AxisConfig,
    AxisLabels,
    BasePlotConfig,
    CanvasConfig,
)
from eventus.visualizers.configs.percentiles_config import PercentilesConfig
from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    validate_alpha,
    validate_choice,
    validate_hex,
    validate_positive_float,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX     = "kde config"
_VALID_BW   = {"scott", "silverman"}


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class KDEStyleConfig:
    """
    Visual style for KDE density curve plots.

    Fields
    ------
    color      : Line and fill color.
    alpha      : Line transparency.
    fill_alpha : Fill area transparency. 0.0 = no fill.
    linewidth  : Line width in points.
    bandwidth  : KDE bandwidth method — 'scott' or 'silverman'.
    show_grid  : Show background grid.
    """
    color:      str   = "#028090"
    alpha:      float = 0.90
    fill_alpha: float = 0.15
    linewidth:  float = 1.5
    bandwidth:  str   = "scott"
    show_grid:  bool  = True

    _PREFIX: ClassVar[str] = "kde style"

    def __post_init__(self) -> None:
        validate_hex(self.color,    "color",    self._PREFIX)
        validate_alpha(self.alpha,              self._PREFIX, "alpha")
        validate_alpha(self.fill_alpha,         self._PREFIX, "fill_alpha")
        validate_positive_float(self.linewidth, self._PREFIX, "linewidth")
        validate_choice(self.bandwidth, _VALID_BW, "bandwidth", self._PREFIX)


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class KDEPlotConfig(BasePlotConfig):
    """
    Full configuration for KDE density curve plots.

    Standalone and reusable — any plotter that draws a KDE curve
    can accept a KDEPlotConfig.

    Example (minimal):
        config = KDEPlotConfig()

    Example (from YAML):
        config = KDEPlotConfig.build_from_yaml("kde.yaml")

    Example (from dict):
        config = KDEPlotConfig.build_from_dict({
            "canvas": {"figsize": [10, 5]},
            "style":  {"color": "#E05C40", "fill_alpha": 0.2},
            "percentiles": {"show": True, "values": [25, 50, 75]},
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    labels:      AxisLabels      = field(default_factory=AxisLabels)
    axes:        AxisConfig      = field(default_factory=AxisConfig)
    style:       KDEStyleConfig  = field(default_factory=KDEStyleConfig)
    percentiles: PercentilesConfig = field(default_factory=PercentilesConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {
        "labels", "axes", "style", "percentiles",
    }

    def __post_init__(self) -> None:
        super().__post_init__()

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "KDEPlotConfig":
        return cls(
            canvas      = canvas,
            labels      = build_section(AxisLabels,       data.get("labels"),      _PREFIX),
            axes        = build_section(AxisConfig,       data.get("axes"),        _PREFIX),
            style       = build_section(KDEStyleConfig,   data.get("style"),       _PREFIX),
            percentiles = build_section(PercentilesConfig, data.get("percentiles"), _PREFIX),
        )

    def __repr__(self) -> str:
        return (
            f"KDEPlotConfig(\n"
            f"  canvas      : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  style       : color={self.style.color}, "
            f"bandwidth={self.style.bandwidth!r}, "
            f"fill_alpha={self.style.fill_alpha}\n"
            f"  percentiles : show={self.percentiles.show}, "
            f"values={self.percentiles.values}\n"
            f")"
        )
