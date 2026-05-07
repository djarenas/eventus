"""
base_plot_config.py

Defines the shared foundation for all plot configuration classes in eventus:

    CanvasConfig        — figsize, dpi, font_size (the physical canvas)
    BasePlotLabels      — title, subtitle
    AxisLabels          — + xlabel, ylabel, units
    AxisConfig          — tick locations, rotation, format strings
    BaseStyleConfig     — alpha
    AxisStyleConfig     — + color, show_grid
    EdgeStyleConfig     — + edgecolor
    BasePlotConfig      — base dataclass all concrete configs inherit from;
                          owns build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, ClassVar

from eventus.visualizers.configs.plot_config_utils import (
    build_section,
    err,
    load_yaml_mapping,
    validate_alpha,
    validate_figsize,
    validate_hex,
    validate_positive_integer,
    validate_sections,
    validate_ticks,
    validate_font_size,
    validate_rotation,
)


# ── Canvas ────────────────────────────────────────────────────────────────────

@dataclass
class CanvasConfig:
    """The physical canvas shared by every plot."""
    figsize:   tuple[float, float] = field(default_factory=lambda: (12.0, 7.0))
    dpi:       int                 = 120
    font_size: int                 = 12

    _PREFIX: ClassVar[str] = "CanvasConfig"

    def __post_init__(self) -> None:
        self.figsize   = validate_figsize(self.figsize, self._PREFIX)
        self.dpi       = validate_positive_integer(self.dpi,       self._PREFIX, "dpi")
        self.font_size = validate_positive_integer(self.font_size, self._PREFIX, "font_size")


# ── Labels ────────────────────────────────────────────────────────────────────

@dataclass
class BasePlotLabels:
    """What is this plot called."""
    title:    str | None = None
    subtitle: str | None = None


@dataclass
class AxisLabels(BasePlotLabels):
    """What are the axes called, and what units are being plotted."""
    # --- Inherited from BasePlotLabels ---
    # title:    str | None
    # subtitle: str | None

    xlabel: str | None = None
    ylabel: str | None = None
    units:  str | None = None   # free-form, e.g. "days", "BMI", "°C"


# ── Axis display ──────────────────────────────────────────────────────────────

@dataclass
class AxisConfig:
    """
    How the axes behave visually.
    Separate concern from AxisLabels: labels answer 'what are the axes called',
    AxisConfig answers 'how do the axes look'.
    """
    x_ticks:         list[float] | None = None   # None → matplotlib auto
    y_ticks:         list[float] | None = None
    x_tick_rotation: float              = 0.0
    y_tick_rotation: float              = 0.0
    x_tick_format:   str | None         = None   # e.g. "{:.0f}", "%Y-%m"
    y_tick_format:   str | None         = None
    tick_font_size:  int | None         = None

    _PREFIX: ClassVar[str] = "AxisConfig"

    def __post_init__(self) -> None:
        self.x_tick_rotation = validate_rotation(self.x_tick_rotation, self._PREFIX)
        self.y_tick_rotation = validate_rotation(self.y_tick_rotation, self._PREFIX)
        self.tick_font_size  = validate_font_size(self.tick_font_size,  self._PREFIX)
        self.x_ticks         = validate_ticks(self.x_ticks,            self._PREFIX)
        self.y_ticks         = validate_ticks(self.y_ticks,            self._PREFIX)


# ── Style ─────────────────────────────────────────────────────────────────────

@dataclass
class BaseStyleConfig:
    """Alpha — the only truly universal style field."""
    alpha: float = 0.85

    _PREFIX: ClassVar[str] = "BaseStyleConfig"

    def __post_init__(self) -> None:
        self.alpha = validate_alpha(self.alpha, self._PREFIX)


@dataclass
class AxisStyleConfig(BaseStyleConfig):
    """Style for axis-based plots: adds color and grid."""
    # --- Inherited from BaseStyleConfig ---
    # alpha: float

    color:     str  = "#028090"
    show_grid: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_hex(self.color, self._PREFIX, "style.color")


@dataclass
class EdgeStyleConfig(AxisStyleConfig):
    """Style for plots that draw bars or patches: adds edgecolor."""
    # --- Inherited from AxisStyleConfig ---
    # alpha:     float
    # color:     str
    # show_grid: bool

    edgecolor: str = "#FFFFFF"

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_hex(self.edgecolor, self._PREFIX, "style.edgecolor")


# ── Base plot config ──────────────────────────────────────────────────────────

@dataclass
class BasePlotConfig:
    """
    Abstract base for all concrete plot configs.

    Enforces:
      - every config has a CanvasConfig under the 'canvas' section
      - YAML load/save and dict build/dump via inherited classmethods

    Concrete configs must:
      - call super().__post_init__() as the first line of their __post_init__
      - define _PREFIX (ClassVar[str]) for error messages
      - define _SECTIONS (ClassVar[set[str]]) listing their valid YAML section names;
        'canvas' is always included automatically
    """
    canvas: CanvasConfig = field(default_factory=CanvasConfig)

    _PREFIX:   ClassVar[str]      = "BasePlotConfig"
    _SECTIONS: ClassVar[set[str]] = set()

    def __post_init__(self) -> None:
        if not isinstance(self.canvas, CanvasConfig):
            raise err(self._PREFIX, "'canvas' must be a CanvasConfig instance")

    # ── YAML / dict I/O ───────────────────────────────────────────────────────

    @classmethod
    def build_from_yaml(cls, path: str | Path) -> "BasePlotConfig":
        """Load a config from a YAML file."""
        data = load_yaml_mapping(path, cls._PREFIX)
        return cls.build_from_dict(data)

    @classmethod
    def build_from_dict(cls, data: dict[str, Any]) -> "BasePlotConfig":
        """
        Build a config from a plain dict.
        Any omitted section falls back to that section's defaults.
        """
        valid_sections = cls._SECTIONS | {"canvas"}
        validate_sections(data, valid_sections, cls._PREFIX)

        canvas_data = data.get("canvas")
        canvas = build_section(CanvasConfig, canvas_data, cls._PREFIX)

        return cls._build_sections(data, canvas)

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "BasePlotConfig":
        """
        Override in concrete configs to build plot-specific sections.
        Always receives the already-constructed CanvasConfig.
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement _build_sections()"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict, suitable for YAML dumping."""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            out[f.name] = self._serialize(v)
        return out

    @staticmethod
    def _serialize(v: Any) -> Any:
        """Recursively serialize a value to a YAML-safe structure."""
        from eventus.visualizers.configs.bins_config import BinsConfig
        if isinstance(v, BinsConfig):
            return dataclasses.asdict(v.spec)
        if dataclasses.is_dataclass(v):
            return {
                k: BasePlotConfig._serialize(fv)
                for k, fv in dataclasses.asdict(v).items()
            }
        if isinstance(v, (list, tuple)):
            return [BasePlotConfig._serialize(i) for i in v]
        return v

    def to_yaml(self, path: str | Path) -> None:
        """Save this config to a YAML file."""
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, sort_keys=False, default_flow_style=False)
