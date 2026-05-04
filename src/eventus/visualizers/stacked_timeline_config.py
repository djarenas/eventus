"""
stacked_timeline_config.py
Configuration for StackedTimelinePlotter.

One YAML drives everything: layout, period of interest bar,
event segments, occurrence markers, legend, and x-axis.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
import yaml

_ERROR_PREFIX = "[StackedTimelineConfig] Error"

# ── Visible defaults ──────────────────────────────────────────────────────
_DEFAULT_ROW_HEIGHT        = 0.5
_DEFAULT_BAR_HEIGHT_RATIO  = 0.84
_DEFAULT_DPI               = 150
_DEFAULT_FONT_SIZE         = 11
_DEFAULT_TITLE_FONT_SIZE   = 13
_DEFAULT_STYLE             = "seaborn-v0_8-whitegrid"
_DEFAULT_X_AXIS            = "auto"
_DEFAULT_MAX_ENTITIES      = 50

_DEFAULT_POI_COLOR         = "#D6E0EA"
_DEFAULT_POI_ALPHA         = 0.6
_DEFAULT_BOUNDARY_COLOR    = "#6B7C93"
_DEFAULT_BOUNDARY_STYLE    = "dashed"

_DEFAULT_EVENT_ALPHA       = 0.85
_DEFAULT_MARKER_SIZE       = 6
_DEFAULT_MARKER_ALPHA      = 0.9

_DEFAULT_LEGEND_LOCATION   = "upper right"
_DEFAULT_LEGEND_FONT_SIZE  = 9

_DEFAULT_DATE_FORMAT       = "%Y-%m"
_DEFAULT_DATE_INTERVAL     = 3
_DEFAULT_N_TICKS           = 10

_DEFAULT_PALETTE = [
    "#028090", "#E05C40", "#6B4FA0", "#E09820",
    "#2C7BB6", "#D7191C", "#1A9641", "#FDAE61",
    "#ABD9E9", "#F46D43",
]

_VALID_X_AXIS      = {"auto", "calendar", "normalized"}
_VALID_MARKERS     = {"circle", "triangle", "square", "diamond", "star"}
_VALID_LINE_STYLES = {"dashed", "dotted", "solid"}
_VALID_LEGEND_LOCS = {
    "upper right", "upper left", "lower right", "lower left",
    "upper center", "lower center", "center left", "center right",
    "center", "best",
}


# ── Helpers ───────────────────────────────────────────────────────────────

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
    """Layout, style, and global plot settings."""
    row_height:         float       = _DEFAULT_ROW_HEIGHT
    bar_height_ratio:   float       = _DEFAULT_BAR_HEIGHT_RATIO
    dpi:                int         = _DEFAULT_DPI
    font_size:          int         = _DEFAULT_FONT_SIZE
    title_font_size:    int         = _DEFAULT_TITLE_FONT_SIZE
    style:              str         = _DEFAULT_STYLE
    title:              str | None  = None
    show_entity_labels: bool        = True
    x_axis:             str         = _DEFAULT_X_AXIS
    max_entities:       int         = _DEFAULT_MAX_ENTITIES
    figsize:            list | None = None
    jitter:             bool        = False
    jitter_ratio:       float       = 0.01

    def __post_init__(self) -> None:
        if self.x_axis not in _VALID_X_AXIS:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.x_axis must be one of "
                f"{sorted(_VALID_X_AXIS)}, got {self.x_axis!r}"
            )
        if not (0.0 < self.bar_height_ratio <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: general.bar_height_ratio must be "
                f"between 0 and 1, got {self.bar_height_ratio}"
            )
        if self.max_entities < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.max_entities must be >= 1, "
                f"got {self.max_entities}"
            )
        if self.figsize is not None and len(self.figsize) != 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: general.figsize must be [width, height], "
                f"got {self.figsize}"
            )
        if not (0.0 < self.jitter_ratio <= 0.5):
            raise ValueError(
                f"{_ERROR_PREFIX}: general.jitter_ratio must be between "
                f"0 and 0.5, got {self.jitter_ratio}"
            )


@dataclass
class POIConfig:
    """
    Period of interest bar settings.

    The bar is divided into segments:
      color_before      — inactive days before first event
      color_active      — days covered by events (set via EventLayerConfig)
      color_middle      — inactive gaps between events
      color_after       — inactive days after last event
      color_no_events   — full bar color when entity has no events at all
    """
    color:            str   = _DEFAULT_POI_COLOR
    color_before:     str   = "#9E9E9E"
    color_middle:     str   = "#F44336"
    color_after:      str   = "#BDBDBD"
    color_no_events:  str   = "#EEEEEE"
    alpha:            float = _DEFAULT_POI_ALPHA
    show_boundaries:  bool  = True
    boundary_color:   str   = _DEFAULT_BOUNDARY_COLOR
    boundary_style:   str   = _DEFAULT_BOUNDARY_STYLE

    def __post_init__(self) -> None:
        for name, val in [
            ("poi_settings.color",           self.color),
            ("poi_settings.color_before",    self.color_before),
            ("poi_settings.color_middle",    self.color_middle),
            ("poi_settings.color_after",     self.color_after),
            ("poi_settings.color_no_events", self.color_no_events),
            ("poi_settings.boundary_color",  self.boundary_color),
        ]:
            _validate_hex(val, name)
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: poi_settings.alpha must be between "
                f"0 and 1, got {self.alpha}"
            )
        if self.boundary_style not in _VALID_LINE_STYLES:
            raise ValueError(
                f"{_ERROR_PREFIX}: poi_settings.boundary_style must be "
                f"one of {sorted(_VALID_LINE_STYLES)}, "
                f"got {self.boundary_style!r}"
            )


@dataclass
class EventLayerConfig:
    """Visual settings for one event identity layer."""
    identity: str
    color:    str         = _DEFAULT_PALETTE[0]
    alpha:    float       = _DEFAULT_EVENT_ALPHA
    label:    str | None  = None

    def __post_init__(self) -> None:
        _validate_hex(self.color, f"events_settings['{self.identity}'].color")
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: events_settings['{self.identity}'].alpha "
                f"must be between 0 and 1, got {self.alpha}"
            )


@dataclass
class OccurrenceLayerConfig:
    """Visual settings for one occurrence identity layer."""
    identity: str
    color:    str         = _DEFAULT_PALETTE[1]
    marker:   str         = "circle"
    size:     int         = _DEFAULT_MARKER_SIZE
    alpha:    float       = _DEFAULT_MARKER_ALPHA
    label:    str | None  = None

    def __post_init__(self) -> None:
        _validate_hex(self.color,
                      f"occurrences_settings['{self.identity}'].color")
        if self.marker not in _VALID_MARKERS:
            raise ValueError(
                f"{_ERROR_PREFIX}: occurrences_settings['{self.identity}']"
                f".marker must be one of {sorted(_VALID_MARKERS)}, "
                f"got {self.marker!r}"
            )
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: occurrences_settings['{self.identity}']"
                f".alpha must be between 0 and 1, got {self.alpha}"
            )


@dataclass
class LegendConfig:
    """Legend display settings."""
    show:               bool  = True
    location:           str   = _DEFAULT_LEGEND_LOCATION
    font_size:          int   = _DEFAULT_LEGEND_FONT_SIZE
    show_poi_in_legend: bool  = False
    outside:            bool  = True

    def __post_init__(self) -> None:
        if self.location not in _VALID_LEGEND_LOCS:
            raise ValueError(
                f"{_ERROR_PREFIX}: legend.location must be one of "
                f"{sorted(_VALID_LEGEND_LOCS)}, got {self.location!r}"
            )


_VALID_X_UNITS = {"days", "months", "years"}

@dataclass
class XAxisConfig:
    """
    X-axis tick spacing settings.

    Two fields control everything:
      unit     — "days", "months", or "years"
      interval — tick every N of that unit

    Examples
    --------
    Tick every 3 months:   unit: months  interval: 3
    Tick every 30 days:    unit: days    interval: 30
    Tick every year:       unit: years   interval: 1

    Works in both calendar and normalized mode.
    format is only used in calendar mode (strftime).
    """
    format:   str = _DEFAULT_DATE_FORMAT
    unit:     str = "months"
    interval: int = 3

    def __post_init__(self) -> None:
        if self.unit not in _VALID_X_UNITS:
            raise ValueError(
                f"{_ERROR_PREFIX}: x_axis_labels.unit must be one of "
                f"{sorted(_VALID_X_UNITS)}, got {self.unit!r}"
            )
        if self.interval < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: x_axis_labels.interval must be >= 1, "
                f"got {self.interval}"
            )


# ── Main config class ─────────────────────────────────────────────────────

@dataclass
class StackedTimelineConfig:
    """
    Configuration for StackedTimelinePlotter.

    One YAML drives everything: layout, period of interest bar,
    event segments, occurrence markers, legend, and x-axis.

    Use build_with_defaults() for a sensible starting point.
    Use build_from_yaml(path) for reproducible, version-controlled plots.

    Examples
    --------
    >>> config = StackedTimelineConfig.build_with_defaults()
    >>> config = StackedTimelineConfig.build_from_yaml("config.yaml")
    >>> config.to_yaml("my_config.yaml")
    """

    general:              GeneralConfig               = field(default_factory=GeneralConfig)
    poi_settings:         POIConfig                   = field(default_factory=POIConfig)
    events_settings:      list[EventLayerConfig]      = field(default_factory=list)
    occurrences_settings: list[OccurrenceLayerConfig] = field(default_factory=list)
    legend:               LegendConfig                = field(default_factory=LegendConfig)
    x_axis_labels:        XAxisConfig                 = field(default_factory=XAxisConfig)

    def __post_init__(self) -> None:
        if not isinstance(self.general, GeneralConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: general must be a GeneralConfig object, "
                f"got {type(self.general).__name__}. "
                f"Use GeneralConfig() or build_from_yaml()."
            )
        if not isinstance(self.poi_settings, POIConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: poi_settings must be a POIConfig object, "
                f"got {type(self.poi_settings).__name__}."
            )
        if not isinstance(self.legend, LegendConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: legend must be a LegendConfig object, "
                f"got {type(self.legend).__name__}."
            )
        if not isinstance(self.x_axis_labels, XAxisConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: x_axis_labels must be an XAxisConfig object, "
                f"got {type(self.x_axis_labels).__name__}."
            )
        if not isinstance(self.events_settings, list):
            raise TypeError(
                f"{_ERROR_PREFIX}: events_settings must be a list, "
                f"got {type(self.events_settings).__name__}."
            )
        if not isinstance(self.occurrences_settings, list):
            raise TypeError(
                f"{_ERROR_PREFIX}: occurrences_settings must be a list, "
                f"got {type(self.occurrences_settings).__name__}."
            )

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_with_defaults(cls) -> "StackedTimelineConfig":
        """Return a StackedTimelineConfig with all defaults."""
        return cls(
            general              = GeneralConfig(),
            poi_settings         = POIConfig(),
            events_settings      = [],
            occurrences_settings = [],
            legend               = LegendConfig(),
            x_axis_labels        = XAxisConfig(),
        )

    @classmethod
    def build_from_yaml(cls, path: str) -> "StackedTimelineConfig":
        """
        Build a StackedTimelineConfig from a YAML file.

        Example YAML
        ------------
        general:
          row_height:       0.5
          bar_height_ratio: 0.84
          dpi:              150
          x_axis:           auto
          jitter:           true
          jitter_ratio:     0.01

        poi_settings:
          color_before:    "#9E9E9E"
          color_middle:    "#F44336"
          color_after:     "#BDBDBD"
          color_no_events: "#EEEEEE"

        events_settings:
          - identity: inpatient_hospitalization
            color:    "#028090"

        occurrences_settings:
          - identity: ed_visit
            color:    "#E05C40"
            marker:   circle

        legend:
          show:    true
          outside: true

        x_axis_labels:
          format:   "%Y-%m"
          unit:     months
          interval: 3
        """
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
                f"got {type(raw).__name__}"
            )

        valid_sections = {
            "general", "poi_settings", "events_settings",
            "occurrences_settings", "legend", "x_axis_labels"
        }
        unknown = set(raw.keys()) - valid_sections
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown sections in YAML: "
                f"{sorted(unknown)}. Valid: {sorted(valid_sections)}"
            )

        def _build(klass, data):
            if data is None:
                return klass()
            valid   = set(klass.__dataclass_fields__.keys())
            unknown = set(data.keys()) - valid
            if unknown:
                raise ValueError(
                    f"{_ERROR_PREFIX}: unknown keys in "
                    f"'{klass.__name__}': {sorted(unknown)}"
                )
            return klass(**data)

        events_raw           = raw.get("events_settings") or []
        occurrences_raw      = raw.get("occurrences_settings") or []
        events_settings      = [EventLayerConfig(**e) for e in events_raw]
        occurrences_settings = [OccurrenceLayerConfig(**o) for o in occurrences_raw]

        return cls(
            general              = _build(GeneralConfig,  raw.get("general")),
            poi_settings         = _build(POIConfig,      raw.get("poi_settings")),
            events_settings      = events_settings,
            occurrences_settings = occurrences_settings,
            legend               = _build(LegendConfig,   raw.get("legend")),
            x_axis_labels        = _build(XAxisConfig,    raw.get("x_axis_labels")),
        )

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def get_event_config(self, identity: str) -> EventLayerConfig | None:
        """Return EventLayerConfig for a given identity, or None."""
        for e in self.events_settings:
            if e.identity == identity:
                return e
        return None

    def get_occurrence_config(self, identity: str) -> OccurrenceLayerConfig | None:
        """Return OccurrenceLayerConfig for a given identity, or None."""
        for o in self.occurrences_settings:
            if o.identity == identity:
                return o
        return None

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {
            "general": {
                "row_height":         self.general.row_height,
                "bar_height_ratio":   self.general.bar_height_ratio,
                "dpi":                self.general.dpi,
                "font_size":          self.general.font_size,
                "title_font_size":    self.general.title_font_size,
                "style":              self.general.style,
                "title":              self.general.title,
                "show_entity_labels": self.general.show_entity_labels,
                "x_axis":             self.general.x_axis,
                "max_entities":       self.general.max_entities,
                "figsize":            self.general.figsize,
                "jitter":             self.general.jitter,
                "jitter_ratio":       self.general.jitter_ratio,
            },
            "poi_settings": {
                "color":           self.poi_settings.color,
                "color_before":    self.poi_settings.color_before,
                "color_middle":    self.poi_settings.color_middle,
                "color_after":     self.poi_settings.color_after,
                "color_no_events": self.poi_settings.color_no_events,
                "alpha":           self.poi_settings.alpha,
                "show_boundaries": self.poi_settings.show_boundaries,
                "boundary_color":  self.poi_settings.boundary_color,
                "boundary_style":  self.poi_settings.boundary_style,
            },
            "events_settings": [
                {"identity": e.identity, "color": e.color,
                 "alpha": e.alpha, "label": e.label}
                for e in self.events_settings
            ],
            "occurrences_settings": [
                {"identity": o.identity, "color": o.color,
                 "marker": o.marker, "size": o.size,
                 "alpha": o.alpha, "label": o.label}
                for o in self.occurrences_settings
            ],
            "legend": {
                "show":               self.legend.show,
                "location":           self.legend.location,
                "font_size":          self.legend.font_size,
                "show_poi_in_legend": self.legend.show_poi_in_legend,
                "outside":            self.legend.outside,
            },
            "x_axis_labels": {
                "format":   self.x_axis_labels.format,
                "unit":     self.x_axis_labels.unit,
                "interval": self.x_axis_labels.interval,
            },
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        n_ev     = len(self.events_settings)
        n_occ    = len(self.occurrences_settings)
        ev_color = self.events_settings[0].color if n_ev else "auto"
        return (
            f"StackedTimelineConfig(\n"
            f"  x_axis               : '{self.general.x_axis}'\n"
            f"  row_height           : {self.general.row_height}\n"
            f"  show_entity_labels   : {self.general.show_entity_labels}\n"
            f"  jitter               : {self.general.jitter} "
            f"(ratio={self.general.jitter_ratio})\n"
            f"  events_settings      : {n_ev} layer(s)\n"
            f"  occurrences_settings : {n_occ} layer(s)\n"
            f"  poi colors           : "
            f"before={self.poi_settings.color_before}  "
            f"active={ev_color}  "
            f"middle={self.poi_settings.color_middle}  "
            f"after={self.poi_settings.color_after}\n"
            f"  legend               : show={self.legend.show}\n"
            f")"
        )
