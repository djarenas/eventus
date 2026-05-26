"""
event_result_timing_config.py
Configuration for EventResultTimingPlotter.

Each section maps directly to one plot method:

    histogram     : HistogramPlotConfig             — base config for plot_histogram()
    histogram_per_n : dict[int, HistogramPlotConfig] — per-nth overrides for plot_histogram()
    facet         : FacetConfig                     — subplot layout for plot_histogram()

The plotter resolves the right HistogramPlotConfig for each nth via:
    cfg.histogram_per_n.get(nth, cfg.histogram)

Inherited from BasePlotConfig:
    canvas: CanvasConfig
    build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
    BasePlotConfig,
    CanvasConfig,
)
from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    err,
    validate_positive_float,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "timing config"


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class FacetConfig:
    """
    Subplot layout settings for EventResultTimingPlotter.plot_histogram().

    One subplot is created per nth event, stacked vertically.
    All subplots share the same x-axis scale — computed across all nths
    unless explicit min/max are set on histogram.bins.

    Fields
    ------
    facet_height : Height in inches of each facet row.
    facet_width  : Width in inches of each facet.
    """
    facet_height: float = 3.0
    facet_width:  float = 6.0

    _PREFIX: ClassVar[str] = "timing facet"

    def __post_init__(self) -> None:
        self.facet_height = validate_positive_float(self.facet_height, self._PREFIX, "facet_height")
        self.facet_width  = validate_positive_float(self.facet_width,  self._PREFIX, "facet_width")


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class EventResultTimingConfig(BasePlotConfig):
    """
    Full configuration for EventResultTimingPlotter.

    Acts as an orchestrator — each attribute owns the full configuration
    for exactly one plot method. The canvas is shared across all methods.

    histogram_per_n holds fully constructed HistogramPlotConfig overrides,
    one per nth event. The plotter resolves the right config at runtime:
        cfg.histogram_per_n.get(nth, cfg.histogram)

    Example (minimal):
        config = EventResultTimingConfig()

    Example (from YAML):
        config = EventResultTimingConfig.build_from_yaml("timing_config.yaml")

    Example (from dict):
        config = EventResultTimingConfig.build_from_dict({
            "canvas":    {"figsize": [8, 12]},
            "histogram": {"bins": {"type": "uniform", "n_bins": 52, "min": 0, "max": 365}},
            "histogram_per_n": {
                2: {"style": {"color": "#E05C40"}},
                3: {"style": {"color": "#6B4FA0"}},
            },
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    histogram:       HistogramPlotConfig             = field(default_factory=HistogramPlotConfig)
    histogram_per_n: dict[int, HistogramPlotConfig]  = field(default_factory=dict)
    facet:           FacetConfig                     = field(default_factory=FacetConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {"histogram", "histogram_per_n", "facet"}

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.histogram, HistogramPlotConfig):
            raise err(
                self._PREFIX,
                f"histogram must be a HistogramPlotConfig, "
                f"got {type(self.histogram).__name__}",
            )
        if not isinstance(self.histogram_per_n, dict):
            raise err(self._PREFIX, f"histogram_per_n must be a dict, got {type(self.histogram_per_n).__name__}")
        for key in self.histogram_per_n:
            if not isinstance(key, int) or key < 1:
                raise err(self._PREFIX, f"histogram_per_n keys must be integers >= 1, got {key!r}")
            if not isinstance(self.histogram_per_n[key], HistogramPlotConfig):
                raise err(
                    self._PREFIX,
                    f"histogram_per_n[{key}] must be a HistogramPlotConfig, "
                    f"got {type(self.histogram_per_n[key]).__name__}",
                )

    # ── Build ─────────────────────────────────────────────────────────────────

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "EventResultTimingConfig":
        canvas_data = data.get("canvas")

        histogram = HistogramPlotConfig.build_from_dict(
            {"canvas": canvas_data, **(data.get("histogram") or {})}
        )

        raw_per_n = data.get("histogram_per_n") or {}
        if not isinstance(raw_per_n, dict):
            raise err(
                _PREFIX,
                f"histogram_per_n must be a mapping of int → histogram sections, "
                f"got {type(raw_per_n).__name__}",
            )
        histogram_per_n: dict[int, HistogramPlotConfig] = {}
        for key, val in raw_per_n.items():
            if not isinstance(key, int) or key < 1:
                raise err(_PREFIX, f"histogram_per_n keys must be integers >= 1, got {key!r}")
            histogram_per_n[key] = HistogramPlotConfig.build_from_dict(
                {"canvas": canvas_data, **(val or {})}
            )

        return cls(
            canvas          = canvas,
            histogram       = histogram,
            histogram_per_n = histogram_per_n,
            facet           = build_section(FacetConfig, data.get("facet"), _PREFIX),
        )

    def __repr__(self) -> str:
        n_overrides = len(self.histogram_per_n)
        return (
            f"EventResultTimingConfig(\n"
            f"  canvas          : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  histogram       : bins={self.histogram.bins.type}, color={self.histogram.style.color}\n"
            f"  histogram_per_n : {n_overrides} override(s) — nths: {sorted(self.histogram_per_n.keys())}\n"
            f"  facet           : {self.facet.facet_height}h x {self.facet.facet_width}w\n"
            f")"
        )
