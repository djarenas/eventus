"""
event_result_shape_config.py
Configuration for EventResultShapePlotter.

Each section maps directly to one plot method:

    center_of_mass : HistogramPlotConfig — plot_center_of_mass()
    density        : HistogramPlotConfig — plot_density()
    scatter        : ShapeScatterConfig  — plot_fingerprint()

Inherited from BasePlotConfig:
    canvas: CanvasConfig
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
from eventus.visualizers.configs.bins_config import BinsConfig
from eventus.visualizers.configs.histogram_plot_config import (
    HistogramPlotConfig,
    HistogramStyleConfig,
)
from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    validate_alpha,
    validate_hex,
    validate_positive_integer,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "shape config"


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class ShapeScatterConfig:
    """
    Visual settings for EventResultShapePlotter.plot_fingerprint().

    Quadrant lines divide the burstiness-vs-memory space into four regions:
        top-right    — bursty + persistent
        bottom-right — bursty + alternating
        top-left     — regular + persistent
        bottom-left  — regular + alternating (most common)

    Fields
    ------
    labels               : Title, subtitle, axis labels and units for this plot.
    color                : Marker color.
    alpha                : Marker transparency.
    size                 : Marker size in points.
    show_grid            : Show background grid.
    show_quadrant_lines  : Draw reference lines at burstiness=0 and memory=0.
    quadrant_line_color  : Color for quadrant reference lines.
                           Ignored if show_quadrant_lines=False.
    """
    labels:              AxisLabels = field(default_factory=AxisLabels)
    color:               str        = "#028090"
    alpha:               float      = 0.7
    size:                int        = 40
    show_grid:           bool       = True
    show_quadrant_lines: bool       = True
    quadrant_line_color: str        = "#AAAAAA"

    _PREFIX: ClassVar[str] = "shape scatter"

    def __post_init__(self) -> None:
        validate_hex(self.color,               "color",               self._PREFIX)
        validate_hex(self.quadrant_line_color, "quadrant_line_color", self._PREFIX)
        validate_alpha(self.alpha, self._PREFIX, "alpha")
        self.size = validate_positive_integer(self.size, self._PREFIX, "size")

        if not self.show_quadrant_lines:
            warnings.warn(
                f"[{self._PREFIX}] show_quadrant_lines=False — quadrant_line_color will be ignored.",
                UserWarning, stacklevel=2,
            )


# ── Default histogram factories ───────────────────────────────────────────────

def _default_center_of_mass() -> HistogramPlotConfig:
    """
    Default histogram for plot_center_of_mass().
    Center of mass is normalized to [0, 1]: 0 = front-loaded, 1 = back-loaded.
    """
    return HistogramPlotConfig(
        bins   = BinsConfig.uniform(n_bins=20, min=0.0, max=1.0),
        labels = AxisLabels(
            xlabel = "Center of mass (0=front-loaded, 1=back-loaded)",
            ylabel = "Entities",
        ),
        style  = HistogramStyleConfig(color="#028090"),
    )


def _default_density() -> HistogramPlotConfig:
    """
    Default histogram for plot_density().
    Density = n events / observation duration in days.
    """
    return HistogramPlotConfig(
        bins   = BinsConfig.uniform(n_bins=20, min=0.0),
        labels = AxisLabels(
            xlabel = "Density (events per day)",
            ylabel = "Entities",
        ),
        style  = HistogramStyleConfig(color="#6B4FA0"),
    )


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class EventResultShapeConfig(BasePlotConfig):
    """
    Full configuration for EventResultShapePlotter.

    Acts as an orchestrator — each attribute owns the full configuration
    for exactly one plot method. The canvas is shared across all methods.

    Example (minimal):
        config = EventResultShapeConfig()

    Example (from YAML):
        config = EventResultShapeConfig.build_from_yaml("shape_config.yaml")

    Example (from dict):
        config = EventResultShapeConfig.build_from_dict({
            "canvas":  {"figsize": [10, 5]},
            "scatter": {"color": "#E05C40", "show_quadrant_lines": True},
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    center_of_mass: HistogramPlotConfig = field(default_factory=_default_center_of_mass)
    density:        HistogramPlotConfig = field(default_factory=_default_density)
    scatter:        ShapeScatterConfig  = field(default_factory=ShapeScatterConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {"center_of_mass", "density", "scatter"}

    def __post_init__(self) -> None:
        super().__post_init__()

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "EventResultShapeConfig":
        # Pass canvas down into each sub-histogram so dpi/font_size stay consistent
        canvas_data = {"canvas": data.get("canvas")}

        center_of_mass_data = data.get("center_of_mass")
        center_of_mass = (
            HistogramPlotConfig.build_from_dict({**canvas_data, **center_of_mass_data})
            if center_of_mass_data is not None
            else _default_center_of_mass()
        )

        density_data = data.get("density")
        density = (
            HistogramPlotConfig.build_from_dict({**canvas_data, **density_data})
            if density_data is not None
            else _default_density()
        )

        # scatter contains a nested labels section — build it explicitly
        scatter_data = data.get("scatter") or {}
        labels_data  = scatter_data.get("labels")
        labels       = build_section(AxisLabels, labels_data, _PREFIX)
        scatter_rest = {k: v for k, v in scatter_data.items() if k != "labels"}
        scatter      = ShapeScatterConfig(labels=labels, **scatter_rest)

        return cls(
            canvas         = canvas,
            center_of_mass = center_of_mass,
            density        = density,
            scatter        = scatter,
        )

    def __repr__(self) -> str:
        return (
            f"EventResultShapeConfig(\n"
            f"  canvas         : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  center_of_mass : bins={self.center_of_mass.bins.type}, color={self.center_of_mass.style.color}\n"
            f"  density        : bins={self.density.bins.type}, color={self.density.style.color}\n"
            f"  scatter        : color={self.scatter.color}, show_quadrant_lines={self.scatter.show_quadrant_lines}\n"
            f")"
        )
