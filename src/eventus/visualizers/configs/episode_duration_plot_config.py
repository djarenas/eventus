"""
episode_duration_plot_config.py
EpisodeDurationPlotConfig — orchestrator config for EpisodeDurationHistogramPlotter.

One YAML file configures both plot methods:
    histogram : HistogramPlotConfig  — for plot_histogram()
    kde       : KDEPlotConfig        — for plot_kde()

The canvas is shared — figsize, dpi, and font_size propagate into both
sub-configs at build time for visual consistency.

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
from eventus.visualizers.configs.kde_plot_config import KDEPlotConfig
from eventus.visualizers.configs.plot_config_utils import err

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "episode duration plot config"


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class EpisodeDurationPlotConfig(BasePlotConfig):
    """
    Orchestrator config for EpisodeDurationHistogramPlotter.

    Each attribute owns the full configuration for exactly one plot
    method. The canvas is shared across both — figsize, dpi, and
    font_size propagate into each sub-config at build time.

    Example (minimal):
        config = EpisodeDurationPlotConfig()

    Example (from YAML):
        config = EpisodeDurationPlotConfig.build_from_yaml("duration.yaml")

    Example (from dict):
        config = EpisodeDurationPlotConfig.build_from_dict({
            "canvas": {"figsize": [10, 6]},
            "histogram": {
                "bins":  {"type": "uniform", "n_bins": 30, "min": 0, "max": 365},
                "style": {"color": "#028090"},
            },
            "kde": {
                "style": {"color": "#028090", "fill_alpha": 0.15},
            },
        })

    Usage
    -----
    >>> plotter = EpisodeDurationHistogramPlotter(result, config)
    >>> plotter.plot_histogram("duration_histogram.png")
    >>> plotter.plot_kde("duration_kde.png")
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    histogram: HistogramPlotConfig = field(default_factory=HistogramPlotConfig)
    kde:       KDEPlotConfig       = field(default_factory=KDEPlotConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {"histogram", "kde"}

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.histogram, HistogramPlotConfig):
            raise err(
                self._PREFIX,
                f"histogram must be a HistogramPlotConfig, "
                f"got {type(self.histogram).__name__}",
            )
        if not isinstance(self.kde, KDEPlotConfig):
            raise err(
                self._PREFIX,
                f"kde must be a KDEPlotConfig, "
                f"got {type(self.kde).__name__}",
            )

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "EpisodeDurationPlotConfig":
        # Propagate canvas into both sub-configs for visual consistency
        canvas_data = data.get("canvas")

        histogram = HistogramPlotConfig.build_from_dict(
            {"canvas": canvas_data, **(data.get("histogram") or {})}
        )
        kde = KDEPlotConfig.build_from_dict(
            {"canvas": canvas_data, **(data.get("kde") or {})}
        )

        return cls(
            canvas    = canvas,
            histogram = histogram,
            kde       = kde,
        )

    def __repr__(self) -> str:
        return (
            f"EpisodeDurationPlotConfig(\n"
            f"  canvas    : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  histogram : bins={self.histogram.bins.type}, "
            f"color={self.histogram.style.color}\n"
            f"  kde       : bandwidth={self.kde.style.bandwidth!r}, "
            f"color={self.kde.style.color}\n"
            f")"
        )
