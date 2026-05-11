"""
stacked_timeline_config.py

StackedTimelineConfig — full configuration for StackedTimelinePlotter in eventus.

Section dataclasses (all validated on construction):
    StackedTimelineLabels  — title, subtitle, title_font_size
    LayoutConfig           — row/bar geometry, style, entity display, jitter
    TimelineAxisConfig     — x-axis mode, tick unit/interval/format, tick_font_size
    POIConfig              — period-of-interest bar colors and boundaries
    EventLayerConfig       — visual settings for one event identity layer
    OccurrenceLayerConfig  — visual settings for one occurrence identity layer
    LegendConfig           — legend display and placement

Inherited from BasePlotConfig:
    canvas: CanvasConfig   ← figsize, dpi, font_size
    build_from_yaml / build_from_dict / to_yaml / to_dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import (
    AxisConfig,
    BasePlotConfig,
    BasePlotLabels,
    CanvasConfig,
)
from eventus.visualizers.configs.plot_config_utils import (
    _DEFAULT_PALETTE,
    build_section,
    err,
    validate_alpha,
    validate_choice,
    validate_hex,
    validate_positive_integer,
    validate_positive_float
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX = "StackedTimelineConfig"

_VALID_X_AXIS_MODES = {"auto", "calendar", "normalized"}
_VALID_X_UNITS      = {"days", "months", "years"}
_VALID_LINE_STYLES  = {"dashed", "dotted", "solid"}
_VALID_MARKERS      = {"circle", "triangle", "square", "diamond", "star"}
_VALID_LEGEND_LOCS  = {
    "upper right", "upper left", "lower right", "lower left",
    "upper center", "lower center", "center left", "center right",
    "center", "best",
}


# ── Section dataclasses ───────────────────────────────────────────────────────

@dataclass
class StackedTimelineLabels(BasePlotLabels):
    """
    Text labels for stacked timeline plots.
    title_font_size lives here because it is a rendering property of the
    title label, not a global canvas concern.
    """
    # --- Inherited from BasePlotLabels ---
    # title:    str | None
    # subtitle: str | None

    title_font_size: int = 13

    _ERROR = "Error in Labels for StackedTimelineConfig"

    def __post_init__(self) -> None:
        self.title_font_size = validate_positive_integer(self.title_font_size, self._ERROR)

@dataclass
class LayoutConfig:
    """
    Timeline-specific layout geometry and display settings.
    Canvas-level fields (figsize, dpi, font_size) live on CanvasConfig.
    """
    row_height:         float = 0.5
    bar_height_ratio:   float = 0.84
    style:              str   = "seaborn-v0_8-whitegrid"
    show_entity_labels: bool  = True
    max_entities:       int   = 100
    jitter:             bool  = False
    jitter_ratio:       float = 0.01

    _PREFIX = "StackedTimelineConfig LayoutConfig"

    def __post_init__(self) -> None:
        self.row_height = validate_positive_float(self.row_height, self._PREFIX, "row_height")
        self.bar_height_ratio = validate_positive_float(self.bar_height_ratio, self._PREFIX, "bar_height_ratio" )
        self.max_entities = validate_positive_integer(self.max_entities, self._PREFIX, "max_entities")
        self.jitter_ratio = validate_positive_float(self.jitter_ratio, self._PREFIX, "jitter_ratio")

        if not (0.0 < self.bar_height_ratio <= 1.0):
            raise err(
                self._ERROR,
                f"layout.bar_height_ratio must be between 0 and 1, "
                f"got {self.bar_height_ratio}",
            )
        if self.max_entities < 1:
            raise err(
                _PREFIX,
                f"layout.max_entities must be >= 1, got {self.max_entities}",
            )
        if not (0.0 < self.jitter_ratio <= 0.5):
            raise err(
                _PREFIX,
                f"layout.jitter_ratio must be between 0 and 0.5, "
                f"got {self.jitter_ratio}",
            )


@dataclass
class TimelineAxisConfig(AxisConfig):
    """
    X-axis configuration for timeline plots.
    Extends AxisConfig with date-aware tick control: unit and interval
    express tick spacing in calendar terms (e.g. every 3 months).
    format is a strftime string used in calendar mode only.

    Examples:
        Tick every 3 months : unit=months, interval=3
        Tick every 30 days  : unit=days,   interval=30
        Tick every year     : unit=years,  interval=1
    """
    # --- Inherited from AxisConfig ---
    # x_ticks:         list[float] | None
    # y_ticks:         list[float] | None
    # x_tick_rotation: float
    # y_tick_rotation: float
    # x_tick_format:   str | None
    # y_tick_format:   str | None
    # tick_fonts_size: int | None

    mode:     str = "auto"       # auto | calendar | normalized
    unit:     str = "months"     # days | months | years
    interval: int = 3
    format:   str = "%Y-%m"      # strftime, used in calendar mode only

    _PREFIX = "StackedTimelineConfig TimeAxis"

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_choice(self.mode,     _VALID_X_AXIS_MODES, "x_axis.mode", self._PREFIX)
        validate_choice(self.unit,     _VALID_X_UNITS,      "x_axis.unit", self._PREFIX)
        self.interval = validate_positive_integer(self.interval, self._PREFIX, "interval")
        if self.interval < 1:
            raise err(self._PREFIX, f"x_axis.interval must be >= 1, got {self.interval}")


@dataclass
class POIConfig:
    """
    Period-of-interest bar settings.

    The bar is divided into segments:
        color_before     — inactive days before the first event
        color_active     — days covered by events (driven by EventLayerConfig)
        color_middle     — inactive gaps between events
        color_after      — inactive days after the last event
        color_no_events  — full bar color when the entity has no events at all
    """
    color:           str   = "#D6E0EA"
    color_before:    str   = "#9E9E9E"
    color_middle:    str   = "#F44336"
    color_after:     str   = "#BDBDBD"
    color_no_events: str   = "#EEEEEE"
    alpha:           float = 0.6
    show_boundaries: bool  = True
    boundary_color:  str   = "#6B7C93"
    boundary_style:  str   = "dashed"

    _PREFIX= "[StackedTimelineConfig] POI"

    def __post_init__(self) -> None:
        for field_name, value in [
            ("poi.color",           self.color),
            ("poi.color_before",    self.color_before),
            ("poi.color_middle",    self.color_middle),
            ("poi.color_after",     self.color_after),
            ("poi.color_no_events", self.color_no_events),
            ("poi.boundary_color",  self.boundary_color),
        ]:
            validate_hex(value, field_name, self._PREFIX)
        self.alpha = validate_alpha(self.alpha, self._PREFIX)
        validate_choice(
            self.boundary_style, _VALID_LINE_STYLES,
            "poi.boundary_style", _PREFIX,
        )


@dataclass
class EventLayerConfig:
    """Visual settings for one event identity layer."""
    identity: str
    color:    str        = _DEFAULT_PALETTE[0]
    alpha:    float      = 0.85
    label:    str | None = None

    _PREFIX = "[StackedTimelineConfig] Event Layers"

    def __post_init__(self) -> None:
        validate_hex(self.color, f"events['{self.identity}'].color", self._PREFIX)
        self.alpha = validate_alpha(self.alpha, self._PREFIX)


@dataclass
class OccurrenceLayerConfig:
    """Visual settings for one occurrence identity layer."""
    identity: str
    color:    str        = _DEFAULT_PALETTE[1]
    marker:   str        = "circle"
    size:     int        = 6
    alpha:    float      = 0.9
    label:    str | None = None

    _PREFIX = "[StackedTimelineConfig] Event Layers"

    def __post_init__(self) -> None:
        validate_hex(self.color, f"occurrences['{self.identity}'].color", self._PREFIX)
        validate_choice(
            self.marker, _VALID_MARKERS,
            f"occurrences['{self.identity}'].marker", self._PREFIX,
        )
        try:
            validate_positive_integer(self.size, self._PREFIX)
        except Exception as e:
            raise ValueError(f"error with size in occurrence layer: {e}")
        validate_alpha(self.alpha,   f"occurrences['{self.identity}'].alpha", self._PREFIX)


@dataclass
class LegendConfig:
    """Legend display and placement."""
    show:               bool = True
    location:           str  = "upper right"
    font_size:          int  = 9
    show_poi_in_legend: bool = False
    outside:            bool = True

    _PREFIX = "[StackedTimelineConfig] Legend"

    def __post_init__(self) -> None:
        validate_choice(self.location, _VALID_LEGEND_LOCS, "legend.location", _PREFIX)
        self.font_size = validate_positive_integer(self.font_size, self._PREFIX, "font_size")


# ── Concrete config ───────────────────────────────────────────────────────────

@dataclass
class StackedTimelineConfig(BasePlotConfig):
    """
    Full configuration for StackedTimelinePlotter.

    Example (minimal — all defaults):
        config = StackedTimelineConfig()

    Example (from YAML):
        config = StackedTimelineConfig.build_from_yaml("my_config.yaml")

    Example (from dict):
        config = StackedTimelineConfig.build_from_dict({
            "canvas": {"figsize": [18, 10]},
            "layout":  {"row_height": 0.6, "jitter": True},
            "events":  [{"identity": "inpatient", "color": "#028090"}],
        })
    """
    # Attribute Declarations

    # canvas: CanvasConfig      ← figsize, dpi, font_size     # --- Inherited from BasePlotConfig ---
    labels:      StackedTimelineLabels        = field(default_factory=StackedTimelineLabels)
    layout:      LayoutConfig                 = field(default_factory=LayoutConfig)
    x_axis:      TimelineAxisConfig           = field(default_factory=TimelineAxisConfig)
    poi:         POIConfig                    = field(default_factory=POIConfig)
    events:      list[EventLayerConfig]       = field(default_factory=list)
    occurrences: list[OccurrenceLayerConfig]  = field(default_factory=list)
    legend:      LegendConfig                 = field(default_factory=LegendConfig)

    _PREFIX:   ClassVar[str]      = _PREFIX
    _SECTIONS: ClassVar[set[str]] = {
        "labels", "layout", "x_axis", "poi", "events", "occurrences", "legend",
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.events, list):
            raise err(_PREFIX, f"events must be a list, got {type(self.events).__name__}")
        if not isinstance(self.occurrences, list):
            raise err(_PREFIX, f"occurrences must be a list, got {type(self.occurrences).__name__}")

    @classmethod
    def _build_sections(
        cls,
        data: dict[str, Any],
        canvas: CanvasConfig,
    ) -> "StackedTimelineConfig":
        events = [
            EventLayerConfig(**e)
            for e in (data.get("events") or [])
        ]
        occurrences = [
            OccurrenceLayerConfig(**o)
            for o in (data.get("occurrences") or [])
        ]
        return cls(
            canvas     = canvas,
            labels      = build_section(StackedTimelineLabels, data.get("labels"),  _PREFIX),
            layout      = build_section(LayoutConfig,          data.get("layout"),  _PREFIX),
            x_axis      = build_section(TimelineAxisConfig,    data.get("x_axis"),  _PREFIX),
            poi         = build_section(POIConfig,             data.get("poi"),     _PREFIX),
            events      = events,
            occurrences = occurrences,
            legend      = build_section(LegendConfig,          data.get("legend"),  _PREFIX),
        )

    # ── Lookup helpers ────────────────────────────────────────────────────────

    def get_event_config(self, identity: str) -> EventLayerConfig | None:
        """Return the EventLayerConfig for the given identity, or None."""
        return next((e for e in self.events if e.identity == identity), None)

    def get_occurrence_config(self, identity: str) -> OccurrenceLayerConfig | None:
        """Return the OccurrenceLayerConfig for the given identity, or None."""
        return next((o for o in self.occurrences if o.identity == identity), None)

    def __repr__(self) -> str:
        n_ev    = len(self.events)
        n_occ   = len(self.occurrences)
        ev_color = self.events[0].color if n_ev else "auto"
        return (
            f"StackedTimelineConfig(\n"
            f"  canvas     : figsize={self.canvas.figsize}, dpi={self.canvas.dpi}\n"
            f"  layout      : row_height={self.layout.row_height}, "
            f"jitter={self.layout.jitter}\n"
            f"  x_axis      : mode='{self.x_axis.mode}', "
            f"unit={self.x_axis.unit}, interval={self.x_axis.interval}\n"
            f"  poi         : before={self.poi.color_before}, "
            f"active={ev_color}, middle={self.poi.color_middle}\n"
            f"  events      : {n_ev} layer(s)\n"
            f"  occurrences : {n_occ} layer(s)\n"
            f"  legend      : show={self.legend.show}, "
            f"outside={self.legend.outside}\n"
            f")"
        )
