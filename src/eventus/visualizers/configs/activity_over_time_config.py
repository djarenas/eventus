"""
activity_over_time_config.py
Configuration for ActivityOverTimePlotter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
    AxisConfig,
    AxisLabels,
    AxisStyleConfig,
    BasePlotConfig,
    CanvasConfig,
)
from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    err,
    validate_alpha,
    validate_choice,
    validate_hex,
    validate_positive_integer,
    validate_positive_float,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "ActivityOverTimeConfig"

_VALID_X_UNITS   = {"days", "months", "years"}
_VALID_FLOW_MODES = {"bar", "scatter"}


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class TimeConfig:
    """Time axis/tick behavior and optional matplotlib style."""

    x_unit:     str       = "months"
    x_interval: int       = 1
    mpl_style:  str | None = "seaborn-v0_8-whitegrid"

    _PREFIX: ClassVar[str] = "ActivityOverTimeConfig TimeConfig"

    def __post_init__(self) -> None:
        validate_choice(self.x_unit, _VALID_X_UNITS, "time.x_unit", self._PREFIX)
        self.x_interval = validate_positive_integer(self.x_interval, self._PREFIX, "x_interval")


@dataclass
class ActivityLineStyleConfig(AxisStyleConfig):
    """Line panel visual settings."""

    color:      str   = "#028090"
    alpha:      float = 0.85
    show_grid:  bool  = True
    linewidth:  float = 1.5
    fill_alpha: float = 0.15

    _PREFIX: ClassVar[str] = "ActivityOverTimeConfig ActivityLineStyleConfig"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.linewidth  = validate_positive_float(self.linewidth,  self._PREFIX, "linewidth")
        self.fill_alpha = validate_alpha(self.fill_alpha, self._PREFIX, "fill_alpha")


@dataclass
class FlowStyleConfig:
    """Bottom panel (entered/exited) visual settings."""

    enabled:         bool  = True
    mode:            str   = "bar"
    entered_color:   str   = "#4CAF50"
    exited_color:    str   = "#F44336"
    zero_line_color: str   = "#AAAAAA"
    show_y_axis:     bool  = True
    bar_width:       float = 0.8
    max_size:        int   = 200
    min_size:        int   = 20

    _PREFIX: ClassVar[str] = "ActivityOverTimeConfig FlowStyleConfig"

    def __post_init__(self) -> None:
        validate_choice(self.mode, _VALID_FLOW_MODES, "flow_style.mode", self._PREFIX)
        validate_hex(self.entered_color,   "flow_style.entered_color",   self._PREFIX)
        validate_hex(self.exited_color,    "flow_style.exited_color",    self._PREFIX)
        validate_hex(self.zero_line_color, "flow_style.zero_line_color", self._PREFIX)
        if not (0.0 < float(self.bar_width) <= 1.0):
            raise err(self._PREFIX, f"flow_style.bar_width must be in (0, 1], got {self.bar_width}")
        self.max_size = validate_positive_integer(self.max_size, self._PREFIX, "max_size")
        self.min_size = validate_positive_integer(self.min_size, self._PREFIX, "min_size")
        if self.min_size > self.max_size:
            raise err(self._PREFIX, "flow_style.min_size cannot exceed flow_style.max_size")


@dataclass
class ActivityLayoutConfig:
    """Relative subplot heights."""

    top_height_ratio:    int = 4
    bottom_height_ratio: int = 1

    _PREFIX: ClassVar[str] = "ActivityOverTimeConfig ActivityLayoutConfig"

    def __post_init__(self) -> None:
        self.top_height_ratio    = validate_positive_integer(self.top_height_ratio,    self._PREFIX, "layout.top_height_ratio")
        self.bottom_height_ratio = validate_positive_integer(self.bottom_height_ratio, self._PREFIX, "layout.bottom_height_ratio")


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class ActivityOverTimeConfig(BasePlotConfig):
    """
    Full configuration for ActivityOverTimePlotter.

    Example (minimal):
        config = ActivityOverTimeConfig()

    Example (from YAML):
        config = ActivityOverTimeConfig.build_from_yaml("my_config.yaml")

    Example (from dict):
        config = ActivityOverTimeConfig.build_from_dict({
            "canvas":     {"figsize": [14, 8]},
            "time":       {"x_unit": "months", "x_interval": 3},
            "line_style": {"color": "#E05C40"},
        })
    """
    # canvas: CanvasConfig  ← figsize, dpi, font_size  (inherited from BasePlotConfig)

    labels:     AxisLabels              = field(default_factory=AxisLabels)
    time:       TimeConfig              = field(default_factory=TimeConfig)
    axes:       AxisConfig              = field(default_factory=AxisConfig)
    line_style: ActivityLineStyleConfig = field(default_factory=ActivityLineStyleConfig)
    flow_style: FlowStyleConfig         = field(default_factory=FlowStyleConfig)
    layout:     ActivityLayoutConfig    = field(default_factory=ActivityLayoutConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {
        "labels", "time", "axes", "line_style", "flow_style", "layout",
    }

    def __post_init__(self) -> None:
        super().__post_init__()

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "ActivityOverTimeConfig":
        return cls(
            canvas     = canvas,
            labels     = build_section(AxisLabels,              data.get("labels"),     _PREFIX),
            time       = build_section(TimeConfig,              data.get("time"),       _PREFIX),
            axes       = build_section(AxisConfig,              data.get("axes"),       _PREFIX),
            line_style = build_section(ActivityLineStyleConfig, data.get("line_style"), _PREFIX),
            flow_style = build_section(FlowStyleConfig,         data.get("flow_style"), _PREFIX),
            layout     = build_section(ActivityLayoutConfig,    data.get("layout"),     _PREFIX),
        )

    def __repr__(self) -> str:
        return (
            f"ActivityOverTimeConfig(\n"
            f"  canvas     : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  time       : x_unit={self.time.x_unit!r}, x_interval={self.time.x_interval}\n"
            f"  line_style : color={self.line_style.color}, alpha={self.line_style.alpha}\n"
            f"  flow_style : mode={self.flow_style.mode!r}, enabled={self.flow_style.enabled}\n"
            f"  layout     : top={self.layout.top_height_ratio}, bottom={self.layout.bottom_height_ratio}\n"
            f")"
        )
