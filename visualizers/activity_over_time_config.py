"""
activity_over_time_config.py
Configuration for ActivityOverTimePlotter.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import yaml

_ERROR_PREFIX = "[ActivityOverTimeConfig] Error"

# ── Visible defaults ──────────────────────────────────────────────────────
_DEFAULT_FIGSIZE            = [14, 6]
_DEFAULT_DPI                = 150
_DEFAULT_FONT_SIZE          = 11
_DEFAULT_TITLE_FONT_SIZE    = 13
_DEFAULT_STYLE              = "seaborn-v0_8-whitegrid"
_DEFAULT_X_UNIT             = "months"
_DEFAULT_X_INTERVAL         = 1

_DEFAULT_LINE_COLOR         = "#028090"
_DEFAULT_LINE_WIDTH         = 1.5
_DEFAULT_FILL_ALPHA         = 0.15

_DEFAULT_ENTERED_COLOR      = "#4CAF50"
_DEFAULT_EXITED_COLOR       = "#F44336"
_DEFAULT_ZERO_LINE_COLOR    = "#AAAAAA"

_DEFAULT_TOP_HEIGHT_RATIO   = 4
_DEFAULT_BOTTOM_HEIGHT_RATIO = 1

_VALID_X_UNITS   = {"days", "months", "years"}
_VALID_BAR_STYLES = {"bar", "scatter"}


def _validate_hex(value: str, name: str) -> None:
    if not (isinstance(value, str) and
            value.startswith("#") and len(value) == 7):
        raise ValueError(
            f"{_ERROR_PREFIX}: {name} must be a 7-character hex color "
            f"like '#028090', got {value!r}"
        )


# ── Nested config dataclasses ─────────────────────────────────────────────

@dataclass
class GeneralConfig:
    """Layout, style, and x-axis settings."""
    figsize:          list       = field(default_factory=lambda: _DEFAULT_FIGSIZE)
    dpi:              int        = _DEFAULT_DPI
    font_size:        int        = _DEFAULT_FONT_SIZE
    title_font_size:  int        = _DEFAULT_TITLE_FONT_SIZE
    style:            str        = _DEFAULT_STYLE
    title:            str | None = None
    x_unit:           str        = _DEFAULT_X_UNIT
    x_interval:       int        = _DEFAULT_X_INTERVAL

    def __post_init__(self) -> None:
        if self.x_unit not in _VALID_X_UNITS:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.x_unit must be one of "
                f"{sorted(_VALID_X_UNITS)}, got {self.x_unit!r}"
            )
        if self.x_interval < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.x_interval must be >= 1, "
                f"got {self.x_interval}"
            )
        if len(self.figsize) != 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.figsize must be [width, height], "
                f"got {self.figsize}"
            )


@dataclass
class LineConfig:
    """Activity line settings."""
    color:       str   = _DEFAULT_LINE_COLOR
    linewidth:   float = _DEFAULT_LINE_WIDTH
    fill_alpha:  float = _DEFAULT_FILL_ALPHA

    def __post_init__(self) -> None:
        _validate_hex(self.color, "line.color")
        if not (0.0 <= self.fill_alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: line.fill_alpha must be between "
                f"0 and 1, got {self.fill_alpha}"
            )


@dataclass
class ArrowConfig:
    """Entry/exit panel settings."""
    show:            bool  = True
    style:           str   = "bar"          # "bar" (diverging) or "scatter"
    entered_color:   str   = _DEFAULT_ENTERED_COLOR
    exited_color:    str   = _DEFAULT_EXITED_COLOR
    zero_line_color: str   = _DEFAULT_ZERO_LINE_COLOR
    show_y_axis:     bool  = True
    bar_width:       float = 0.8            # fraction of tick interval
    # scatter-only settings (ignored when style="bar")
    max_size:        int   = 200
    min_size:        int   = 20

    def __post_init__(self) -> None:
        if self.style not in _VALID_BAR_STYLES:
            raise ValueError(
                f"{_ERROR_PREFIX}: arrows.style must be one of "
                f"{sorted(_VALID_BAR_STYLES)}, got {self.style!r}"
            )
        _validate_hex(self.entered_color,   "arrows.entered_color")
        _validate_hex(self.exited_color,    "arrows.exited_color")
        _validate_hex(self.zero_line_color, "arrows.zero_line_color")


@dataclass
class LayoutConfig:
    """Subplot height ratios."""
    top_height_ratio:    int = _DEFAULT_TOP_HEIGHT_RATIO
    bottom_height_ratio: int = _DEFAULT_BOTTOM_HEIGHT_RATIO

    def __post_init__(self) -> None:
        if self.top_height_ratio < 1 or self.bottom_height_ratio < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: layout height ratios must be >= 1"
            )


# ── Main config class ─────────────────────────────────────────────────────

@dataclass
class ActivityOverTimeConfig:
    """
    Configuration for ActivityOverTimePlotter.

    Controls the activity line panel, the entry/exit panel,
    x-axis tick spacing, and figure layout.

    Examples
    --------
    >>> config = ActivityOverTimeConfig.build_with_defaults()
    >>> config = ActivityOverTimeConfig.build_from_yaml("config.yaml")
    >>> config.to_yaml("my_config.yaml")
    """
    general: GeneralConfig = field(default_factory=GeneralConfig)
    line:    LineConfig    = field(default_factory=LineConfig)
    arrows:  ArrowConfig   = field(default_factory=ArrowConfig)
    layout:  LayoutConfig  = field(default_factory=LayoutConfig)

    @classmethod
    def build_with_defaults(cls) -> "ActivityOverTimeConfig":
        """Return a config with all defaults."""
        return cls(
            general = GeneralConfig(),
            line    = LineConfig(),
            arrows  = ArrowConfig(),
            layout  = LayoutConfig(),
        )

    @classmethod
    def build_from_yaml(cls, path: str) -> "ActivityOverTimeConfig":
        """Build config from a YAML file."""
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
                f"got {type(raw).__name__}"
            )

        valid_sections = {"general", "line", "arrows", "layout"}
        unknown = set(raw.keys()) - valid_sections
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown sections: {sorted(unknown)}"
            )

        def _build(klass, data):
            if data is None:
                return klass()
            unknown = set(data.keys()) - set(klass.__dataclass_fields__.keys())
            if unknown:
                raise ValueError(
                    f"{_ERROR_PREFIX}: unknown keys in "
                    f"'{klass.__name__}': {sorted(unknown)}"
                )
            return klass(**data)

        return cls(
            general = _build(GeneralConfig, raw.get("general")),
            line    = _build(LineConfig,    raw.get("line")),
            arrows  = _build(ArrowConfig,   raw.get("arrows")),
            layout  = _build(LayoutConfig,  raw.get("layout")),
        )

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {
            "general": {
                "figsize":         self.general.figsize,
                "dpi":             self.general.dpi,
                "font_size":       self.general.font_size,
                "title_font_size": self.general.title_font_size,
                "style":           self.general.style,
                "title":           self.general.title,
                "x_unit":          self.general.x_unit,
                "x_interval":      self.general.x_interval,
            },
            "line": {
                "color":       self.line.color,
                "linewidth":   self.line.linewidth,
                "fill_alpha":  self.line.fill_alpha,
            },
            "arrows": {
                "show":            self.arrows.show,
                "style":           self.arrows.style,
                "entered_color":   self.arrows.entered_color,
                "exited_color":    self.arrows.exited_color,
                "zero_line_color": self.arrows.zero_line_color,
                "show_y_axis":     self.arrows.show_y_axis,
                "bar_width":       self.arrows.bar_width,
                "max_size":        self.arrows.max_size,
                "min_size":        self.arrows.min_size,
            },
            "layout": {
                "top_height_ratio":    self.layout.top_height_ratio,
                "bottom_height_ratio": self.layout.bottom_height_ratio,
            },
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        return (
            f"ActivityOverTimeConfig(\n"
            f"  x_unit    : '{self.general.x_unit}'\n"
            f"  x_interval: {self.general.x_interval}\n"
            f"  line      : color={self.line.color} "
            f"fill_alpha={self.line.fill_alpha}\n"
            f"  arrows    : show={self.arrows.show} "
            f"style={self.arrows.style!r}\n"
            f")"
        )
