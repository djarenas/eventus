"""
histogram_config.py
HistogramConfig — configuration for histogram plots in eventus.
One YAML drives everything: bins, labels, style, percentile lines,
and optional stratification.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import yaml

_ERROR_PREFIX = "[HistogramConfig] Error"

_VALID_BIN_TYPES   = {"fixed_width", "percentile", "log", "custom"}
_VALID_LINESTYLES  = {"dashed", "dotted", "solid"}
_VALID_STRAT_STYLES = {"overlay", "facet"}

_DEFAULT_PALETTE = [
    "#028090", "#E05C40", "#6B4FA0", "#E09820", "#2C7BB6",
    "#D7191C", "#1A9641", "#FDAE61", "#ABD9E9", "#F46D43",
]


# ── Nested config dataclasses ─────────────────────────────────────────────

@dataclass
class BinsConfig:
    """
    Controls histogram bin edges.

    type : str
        "fixed_width" — bins of equal width (requires width > 0)
        "percentile"  — bin edges at data percentiles
        "log"         — logarithmically spaced bins
        "custom"      — explicit list of breakpoints (requires edges)
    width : float | None
        Bin width for fixed_width. Required if type="fixed_width".
    min : float | None
        Left edge of first bin. Optional for fixed_width.
    max : float | None
        Right edge of last bin. Optional for fixed_width.
    edges : list[float] | None
        Explicit bin edges for custom type.
    n_bins : int
        Number of bins for percentile or log types. Default 20.
    """
    type:   str         = "fixed_width"
    width:  float | None = 7.0
    min:    float | None = 0.0
    max:    float | None = 365.0
    edges:  list        = field(default_factory=list)
    n_bins: int         = 20

    def __post_init__(self) -> None:
        if self.type not in _VALID_BIN_TYPES:
            raise ValueError(
                f"{_ERROR_PREFIX}: bins.type must be one of "
                f"{sorted(_VALID_BIN_TYPES)}, got {self.type!r}"
            )
        if self.type == "fixed_width" and (self.width is None or self.width <= 0):
            raise ValueError(
                f"{_ERROR_PREFIX}: bins.width must be > 0 when type='fixed_width'"
            )
        if self.type == "custom" and not self.edges:
            raise ValueError(
                f"{_ERROR_PREFIX}: bins.edges must be provided when type='custom'"
            )
        if self.n_bins <= 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: bins.n_bins must be > 0, got {self.n_bins}"
            )


@dataclass
class LabelsConfig:
    """
    Controls histogram text labels.
    title and xlabel default to None — callers auto-fill from identity if null.
    """
    title:    str | None = None
    xlabel:   str | None = None
    ylabel:   str        = "Count"
    subtitle: str | None = None


@dataclass
class StyleConfig:
    """Controls histogram visual appearance."""
    color:     str        = "#028090"
    edgecolor: str        = "#FFFFFF"
    alpha:     float      = 0.85
    figsize:   list       = field(default_factory=lambda: [10, 5])
    dpi:       int        = 150

    def __post_init__(self) -> None:
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(
                f"{_ERROR_PREFIX}: style.alpha must be between 0 and 1, "
                f"got {self.alpha}"
            )
        if self.dpi <= 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.dpi must be > 0, got {self.dpi}"
            )
        if len(self.figsize) != 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: style.figsize must be [width, height], "
                f"got {self.figsize}"
            )
        self._validate_hex(self.color, "style.color")
        self._validate_hex(self.edgecolor, "style.edgecolor")

    def _validate_hex(self, value: str, name: str) -> None:
        if not (value.startswith("#") and len(value) == 7):
            raise ValueError(
                f"{_ERROR_PREFIX}: {name} must be a 7-character hex color "
                f"like '#028090', got {value!r}"
            )


@dataclass
class PercentilesConfig:
    """Controls percentile reference lines on the histogram."""
    show:        bool      = True
    values:      list      = field(default_factory=lambda: [25, 50, 75, 90])
    color:       str       = "#333333"
    linestyle:   str       = "dashed"
    show_labels: bool      = True

    def __post_init__(self) -> None:
        if self.linestyle not in _VALID_LINESTYLES:
            raise ValueError(
                f"{_ERROR_PREFIX}: percentile_lines.linestyle must be one of "
                f"{sorted(_VALID_LINESTYLES)}, got {self.linestyle!r}"
            )
        bad = [v for v in self.values if not (0 <= v <= 100)]
        if bad:
            raise ValueError(
                f"{_ERROR_PREFIX}: percentile_lines.values must be between "
                f"0 and 100, got {bad}"
            )


@dataclass
class StratificationConfig:
    """
    Controls stratified histogram appearance.
    Only used when stratify_by is set on the plotter.
    """
    style:          str   = "overlay"
    max_categories: int   = 10
    colors:         dict  = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.style not in _VALID_STRAT_STYLES:
            raise ValueError(
                f"{_ERROR_PREFIX}: stratification.style must be one of "
                f"{sorted(_VALID_STRAT_STYLES)}, got {self.style!r}"
            )
        if self.max_categories < 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: stratification.max_categories must be >= 2, "
                f"got {self.max_categories}"
            )
        # Validate any provided hex colors
        for cat, hex_color in self.colors.items():
            if not (isinstance(hex_color, str) and
                    hex_color.startswith("#") and len(hex_color) == 7):
                raise ValueError(
                    f"{_ERROR_PREFIX}: stratification.colors['{cat}'] must be a "
                    f"7-character hex color like '#028090', got {hex_color!r}"
                )

    def resolve_colors(self, categories: list) -> dict[str, str]:
        """
        Return a color for every category.
        User-provided colors take priority. Missing ones get
        auto-assigned from the default palette with a warning.
        """
        import warnings
        resolved = {}
        palette_idx = 0
        for cat in categories:
            if cat in self.colors:
                resolved[cat] = self.colors[cat]
            else:
                color = _DEFAULT_PALETTE[palette_idx % len(_DEFAULT_PALETTE)]
                warnings.warn(
                    f"[HistogramConfig] No color provided for category "
                    f"'{cat}' — auto-assigning {color}",
                    UserWarning, stacklevel=3,
                )
                resolved[cat] = color
                palette_idx += 1
        return resolved


# ── Main config class ─────────────────────────────────────────────────────

@dataclass
class HistogramConfig:
    """
    Configuration for histogram plots in eventus.

    One YAML drives everything: bins, labels, style, percentile lines,
    and optional stratification settings.

    Use build_with_defaults() for a sensible starting point.
    Use build_from_yaml(path) for reproducible, version-controlled plots.

    Examples
    --------
    >>> config = HistogramConfig.build_with_defaults()
    >>> config = HistogramConfig.build_from_yaml("histogram_config.yaml")
    >>> config.to_yaml("my_histogram_config.yaml")
    """

    bins:             BinsConfig           = field(default_factory=BinsConfig)
    labels:           LabelsConfig         = field(default_factory=LabelsConfig)
    style:            StyleConfig          = field(default_factory=StyleConfig)
    percentile_lines: PercentilesConfig    = field(default_factory=PercentilesConfig)
    stratification:   StratificationConfig = field(default_factory=StratificationConfig)

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_with_defaults(cls) -> "HistogramConfig":
        """
        Return a HistogramConfig with sensible defaults.
        Good starting point for any numeric column in eventus.
        """
        return cls(
            bins             = BinsConfig(),
            labels           = LabelsConfig(),
            style            = StyleConfig(),
            percentile_lines = PercentilesConfig(),
            stratification   = StratificationConfig(),
        )

    @classmethod
    def build_from_yaml(cls, path: str) -> "HistogramConfig":
        """
        Build a HistogramConfig from a YAML file.

        Parameters
        ----------
        path : str
            Path to the YAML config file.

        Example YAML
        ------------
        bins:
          type:  fixed_width
          width: 7
          min:   0
          max:   365

        labels:
          title:  null
          xlabel: "Duration (days)"
          ylabel: "Count"

        style:
          color:    "#028090"
          alpha:    0.85
          figsize:  [10, 5]
          dpi:      150

        percentile_lines:
          show:        true
          values:      [25, 50, 75, 90]
          linestyle:   dashed
          show_labels: true

        stratification:
          style:          overlay
          max_categories: 10
          colors:
            H01: "#028090"
            H02: "#E05C40"
        """
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
                f"got {type(raw).__name__}"
            )

        valid_sections = {"bins", "labels", "style",
                          "percentile_lines", "stratification"}
        unknown = set(raw.keys()) - valid_sections
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown sections in YAML: {sorted(unknown)}. "
                f"Valid sections: {sorted(valid_sections)}"
            )

        def _build(cls_, data):
            if data is None:
                return cls_()
            valid = set(cls_.__dataclass_fields__.keys())
            unknown = set(data.keys()) - valid
            if unknown:
                raise ValueError(
                    f"{_ERROR_PREFIX}: unknown keys in '{cls_.__name__}': "
                    f"{sorted(unknown)}"
                )
            return cls_(**data)

        return cls(
            bins             = _build(BinsConfig,           raw.get("bins")),
            labels           = _build(LabelsConfig,         raw.get("labels")),
            style            = _build(StyleConfig,          raw.get("style")),
            percentile_lines = _build(PercentilesConfig,    raw.get("percentile_lines")),
            stratification   = _build(StratificationConfig, raw.get("stratification")),
        )

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {
            "bins": {
                "type":   self.bins.type,
                "width":  self.bins.width,
                "min":    self.bins.min,
                "max":    self.bins.max,
                "edges":  self.bins.edges,
                "n_bins": self.bins.n_bins,
            },
            "labels": {
                "title":    self.labels.title,
                "xlabel":   self.labels.xlabel,
                "ylabel":   self.labels.ylabel,
                "subtitle": self.labels.subtitle,
            },
            "style": {
                "color":     self.style.color,
                "edgecolor": self.style.edgecolor,
                "alpha":     self.style.alpha,
                "figsize":   self.style.figsize,
                "dpi":       self.style.dpi,
            },
            "percentile_lines": {
                "show":        self.percentile_lines.show,
                "values":      self.percentile_lines.values,
                "color":       self.percentile_lines.color,
                "linestyle":   self.percentile_lines.linestyle,
                "show_labels": self.percentile_lines.show_labels,
            },
            "stratification": {
                "style":          self.stratification.style,
                "max_categories": self.stratification.max_categories,
                "colors":         self.stratification.colors,
            },
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        return (
            f"HistogramConfig(\n"
            f"  bins             : {self.bins.type} "
            f"(width={self.bins.width}, min={self.bins.min}, max={self.bins.max})\n"
            f"  style            : color={self.style.color}, "
            f"alpha={self.style.alpha}, figsize={self.style.figsize}\n"
            f"  percentile_lines : show={self.percentile_lines.show}, "
            f"values={self.percentile_lines.values}\n"
            f"  stratification   : style='{self.stratification.style}', "
            f"max_categories={self.stratification.max_categories}\n"
            f")"
        )
