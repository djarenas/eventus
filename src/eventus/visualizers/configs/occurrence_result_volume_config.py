"""
occurrence_result_volume_config.py
Configuration for OccurrenceResultVolumePlotter.

Each section maps directly to one plot method:

    bar       : CategoryBarConfig          — plot_prevalence_bar()
    count_bar : CountDistributionBarConfig — plot_count_distribution_bar()

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
from eventus.visualizers.configs.bar_config import (
    CategoryBarConfig,
    CountDistributionBarConfig,
)
from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    err,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "volume config"


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class OccurrenceResultVolumeConfig(BasePlotConfig):
    """
    Full configuration for OccurrenceResultVolumePlotter.

    Acts as an orchestrator — each attribute owns the full configuration
    for exactly one plot method. The canvas is shared across all methods.

    Example (minimal):
        config = OccurrenceResultVolumeConfig()

    Example (from YAML):
        config = OccurrenceResultVolumeConfig.build_from_yaml("volume_config.yaml")

    Example (from dict):
        config = OccurrenceResultVolumeConfig.build_from_dict({
            "canvas":    {"figsize": [10, 5]},
            "bar":       {"color_any": "#028090", "show_ci": True},
            "count_bar": {"max_n": 10, "show_as_pct": True},
        })
    """
    # --- Inherited from BasePlotConfig ---
    # canvas: CanvasConfig

    bar:       CategoryBarConfig          = field(default_factory=CategoryBarConfig)
    count_bar: CountDistributionBarConfig = field(default_factory=CountDistributionBarConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {"bar", "count_bar"}

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.bar, CategoryBarConfig):
            raise err(self._PREFIX, f"bar must be a CategoryBarConfig, got {type(self.bar).__name__}")
        if not isinstance(self.count_bar, CountDistributionBarConfig):
            raise err(self._PREFIX, f"count_bar must be a CountDistributionBarConfig, got {type(self.count_bar).__name__}")

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "OccurrenceResultVolumeConfig":
        # bar and count_bar each contain a nested labels section —
        # build_section handles this since AxisLabels is a dataclass field
        bar_data       = data.get("bar")       or {}
        count_bar_data = data.get("count_bar") or {}

        return cls(
            canvas    = canvas,
            bar       = _build_category_bar(bar_data),
            count_bar = _build_count_distribution_bar(count_bar_data),
        )

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultVolumeConfig(\n"
            f"  canvas    : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  bar       : color_any={self.bar.color_any}, show_ci={self.bar.show_ci}\n"
            f"  count_bar : max_n={self.count_bar.max_n}, show_as_pct={self.count_bar.show_as_pct}\n"
            f")"
        )


# ── Section builders ──────────────────────────────────────────────────────────
# CategoryBarConfig and CountDistributionBarConfig contain a nested AxisLabels,
# so they can't use plain build_section — labels must be constructed first.

def _build_category_bar(data: dict) -> CategoryBarConfig:
    from eventus.visualizers.configs.base_plot_config import AxisLabels
    labels_data = data.get("labels")
    labels      = build_section(AxisLabels, labels_data, _PREFIX)
    rest        = {k: v for k, v in data.items() if k != "labels"}
    return CategoryBarConfig(labels=labels, **rest)


def _build_count_distribution_bar(data: dict) -> CountDistributionBarConfig:
    from eventus.visualizers.configs.base_plot_config import AxisLabels
    from eventus.visualizers.configs.percentiles_config import PercentilesConfig
    labels_data      = data.get("labels")
    pct_lines_data   = data.get("percentile_lines")
    labels           = build_section(AxisLabels,        labels_data,    _PREFIX)
    percentile_lines = build_section(PercentilesConfig, pct_lines_data, _PREFIX)
    rest             = {k: v for k, v in data.items() if k not in {"labels", "percentile_lines"}}
    return CountDistributionBarConfig(
        labels           = labels,
        percentile_lines = percentile_lines,
        **rest,
    )
