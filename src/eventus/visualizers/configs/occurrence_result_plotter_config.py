# """
# occurrence_result_plotter_config.py
# Configuration classes for occurrence result plotters in eventus.

# One module, three plotter configs — Volume, Timing, Shape — each composed
# of nested dataclasses. A shared GeneralConfig covers layout and style
# settings common to all three.

# The histogram section of each plotter config is a full HistogramPlotConfig
# (bins, labels, style, percentile lines, stratification) from
# histogram_plots_config.py.

# Classes
# -------
# GeneralConfig                   — shared layout and style settings
# VolumeBarConfig                 — prevalence bar chart settings
# OccurrenceResultVolumeConfig    — full config for OccurrenceResultVolumePlotter
# SurvivalCurveConfig             — KM curve appearance for plot_survival()
# FacetConfig                     — facet layout settings for timing histograms
# OccurrenceResultTimingConfig    — full config for OccurrenceResultTimingPlotter
# ShapeScatterConfig              — scatter plot settings for fingerprint plot
# OccurrenceResultShapeConfig     — full config for OccurrenceResultShapePlotter

# Usage
# -----
# >>> config = OccurrenceResultVolumeConfig()
# >>> config = OccurrenceResultTimingConfig.build_from_yaml("timing_config.yaml")
# >>> config.to_yaml("my_timing_config.yaml")
# """
# from __future__ import annotations

# import dataclasses
# import warnings
# from dataclasses import dataclass, field
# from pathlib import Path

# import yaml

# from eventus.visualizers.histograms.histogram_plot_config import (
#     HistogramPlotConfig,
#     LabelsConfig,
#     StyleConfig,
#     BinsConfig,
# )
# from eventus.visualizers.plot_config_utils import (
#     build_section,
#     err,
#     validate_alpha,
#     validate_figsize,
#     validate_hex,
#     validate_positive,
# )

# # ── Constants ─────────────────────────────────────────────────────────────────

# _PREFIX        = "OccurrenceResultPlotterConfig"
# _DEFAULT_STYLE = "seaborn-v0_8-whitegrid"


# # ── Shorthand wrappers ────────────────────────────────────────────────────────

# def _err(msg: str)                   -> ValueError:         return err(_PREFIX, msg)
# def _hex(v: str, name: str)          -> None:               validate_hex(v, name, _PREFIX)
# def _alpha(v: float, name: str)      -> None:               validate_alpha(v, name, _PREFIX)
# def _pos(v, name: str)               -> None:               validate_positive(v, name, _PREFIX)
# def _figsize(v) -> tuple[float, float]:                     return validate_figsize(v, "figsize", _PREFIX)
# def _section(cls_, data)             :                      return build_section(cls_, data, _PREFIX)


# # ── Base class for top-level plotter configs ──────────────────────────────────

# class _PlotterConfigBase:
#     """
#     Mixin providing build_from_yaml / build_from_dict / to_yaml for all
#     top-level plotter config dataclasses.

#     Subclasses must define:
#       _VALID_SECTIONS : set[str]
#       _build_sections(cls, raw: dict) -> dict   (classmethod)
#     """

#     _VALID_SECTIONS: set[str] = set()

#     @classmethod
#     def build_from_yaml(cls, path: str | Path):
#         """Build from a YAML file. Any omitted section falls back to defaults."""
#         with open(path) as f:
#             raw = yaml.safe_load(f)
#         if not isinstance(raw, dict):
#             raise _err(f"YAML must be a mapping, got {type(raw).__name__}")
#         return cls(**cls._build_sections(raw))

#     @classmethod
#     def build_from_dict(cls, data: dict):
#         """Build from a plain dict. Any omitted section falls back to defaults."""
#         if not isinstance(data, dict):
#             raise _err(f"build_from_dict expects a dict, got {type(data).__name__}")
#         return cls(**cls._build_sections(data))

#     @classmethod
#     def _check_sections(cls, data: dict) -> None:
#         unknown = set(data.keys()) - cls._VALID_SECTIONS
#         if unknown:
#             raise _err(
#                 f"unknown sections: {sorted(unknown)}. "
#                 f"Valid: {sorted(cls._VALID_SECTIONS)}"
#             )

#     @classmethod
#     def _build_sections(cls, data: dict) -> dict:
#         raise NotImplementedError

#     def to_yaml(self, path: str | Path) -> None:
#         """Save this config to a YAML file."""
#         def _coerce(obj):
#             if isinstance(obj, dict):
#                 return {k: _coerce(v) for k, v in obj.items()}
#             if isinstance(obj, (tuple, list)):
#                 return [_coerce(v) for v in obj]
#             return obj

#         with open(path, "w") as f:
#             yaml.dump(_coerce(dataclasses.asdict(self)), f,
#                       sort_keys=False, default_flow_style=False)
#         print(f"Config saved to: {path}")


# # ── Helper: build a HistogramPlotConfig from a raw section dict ───────────────

# def _build_histogram(data: dict | None) -> HistogramPlotConfig:
#     """
#     Build a HistogramPlotConfig from a raw YAML section dict, or return
#     defaults if data is None. Delegates unknown-key checking to
#     HistogramPlotConfig._parse_sections.
#     """
#     if data is None:
#         return HistogramPlotConfig()
#     return HistogramPlotConfig.build_from_dict(data)


# def _merge_histogram(base: HistogramPlotConfig,
#                      override: dict | None) -> HistogramPlotConfig:
#     """
#     Return a new HistogramPlotConfig with override fields merged on top of base.
#     Only the sections present in override are changed; everything else is
#     inherited from base. Used for per-nth histogram overrides in TimingConfig.
#     """
#     if not override:
#         return base
#     base_dict = dataclasses.asdict(base)
#     for section, values in override.items():
#         if section not in base_dict:
#             raise _err(
#                 f"histogram_per_n override contains unknown section "
#                 f"'{section}'. Valid: {sorted(base_dict.keys())}"
#             )
#         if isinstance(values, dict) and isinstance(base_dict[section], dict):
#             base_dict[section].update(values)
#         else:
#             base_dict[section] = values
#     return HistogramPlotConfig.build_from_dict(base_dict)


# # ── Shared GeneralConfig ──────────────────────────────────────────────────────

# @dataclass
# class GeneralConfig:
#     """
#     Shared layout and style settings for all occurrence result plotters.

#     Fields
#     ------
#     title : str | None
#         Main plot title. None = auto-generated from identity.
#     dpi : int
#         Figure resolution. Default 150.
#     font_size : int
#         Base font size for axis labels and ticks. Default 11.
#     title_font_size : int
#         Font size for the plot title. Default 13.
#     style : str
#         Matplotlib style string. Default 'seaborn-v0_8-whitegrid'.
#     figsize : tuple[float, float] | None
#         (width, height) in inches. None = auto-computed per plotter.
#     """
#     title:           str | None                 = None
#     dpi:             int                        = 150
#     font_size:       int                        = 11
#     title_font_size: int                        = 13
#     style:           str                        = _DEFAULT_STYLE
#     figsize:         tuple[float, float] | None = None

#     def __post_init__(self) -> None:
#         _pos(self.dpi,             "general.dpi")
#         _pos(self.font_size,       "general.font_size")
#         _pos(self.title_font_size, "general.title_font_size")
#         if self.figsize is not None:
#             self.figsize = _figsize(self.figsize)
#         if self.title_font_size <= self.font_size:
#             warnings.warn(
#                 f"[{_PREFIX}] general.title_font_size ({self.title_font_size}) "
#                 f"is not larger than font_size ({self.font_size}) — "
#                 "titles may not stand out.",
#                 UserWarning, stacklevel=2,
#             )


# # ── Volume config ─────────────────────────────────────────────────────────────

# @dataclass
# class VolumeBarConfig:
#     """
#     Visual settings for OccurrenceResultVolumePlotter.plot_prevalence_bar().

#     Fields
#     ------
#     color_any : str
#         Bar color for entities with any occurrence. Default '#028090'.
#     color_multiple : str
#         Bar color for entities with multiple occurrences. Default '#E05C40'.
#     color_none : str
#         Bar color for entities with no occurrences. Default '#EEEEEE'.
#     show_pct_labels : bool
#         Annotate each bar with its percentage. Default True.
#     alpha : float
#         Bar transparency. Default 0.85.
#     show_ci : bool
#         Draw Wilson confidence interval error bars. Default True.
#     ci_alpha : float
#         CI error bar transparency. Default 0.8.
#     ci_color : str
#         CI error bar color. Default '#333333'.
#     """
#     color_any:       str   = "#028090"
#     color_multiple:  str   = "#E05C40"
#     color_none:      str   = "#EEEEEE"
#     show_pct_labels: bool  = True
#     alpha:           float = 0.85
#     show_ci:         bool  = True
#     ci_alpha:        float = 0.8
#     ci_color:        str   = "#333333"

#     def __post_init__(self) -> None:
#         _hex(self.color_any,      "bar.color_any")
#         _hex(self.color_multiple, "bar.color_multiple")
#         _hex(self.color_none,     "bar.color_none")
#         _hex(self.ci_color,       "bar.ci_color")
#         _alpha(self.alpha,        "bar.alpha")
#         _alpha(self.ci_alpha,     "bar.ci_alpha")

#         if not self.show_ci and self.ci_alpha != 0.8:
#             warnings.warn(
#                 f"[{_PREFIX}] bar.show_ci=False but ci_alpha is set "
#                 "— it will be ignored.",
#                 UserWarning, stacklevel=2,
#             )


# @dataclass
# class OccurrenceResultVolumeConfig(_PlotterConfigBase):
#     """
#     Configuration for OccurrenceResultVolumePlotter.

#     Sections
#     --------
#     general   : GeneralConfig         — layout and style
#     histogram : HistogramPlotConfig   — for plot_histogram()
#     bar       : VolumeBarConfig       — for plot_prevalence_bar()

#     Usage
#     -----
#     >>> config = OccurrenceResultVolumeConfig()
#     >>> config = OccurrenceResultVolumeConfig.build_from_yaml("volume_config.yaml")
#     >>> config.to_yaml("volume_config.yaml")

#     Example YAML
#     ------------
#     general:
#       title:     null
#       dpi:       150
#       font_size: 11
#       style:     "seaborn-v0_8-whitegrid"

#     histogram:
#       bins:
#         type:  fixed_width
#         width: 1
#         min:   0
#         max:   20
#       labels:
#         xlabel: "Number of occurrences"
#         ylabel: "Entities"
#       style:
#         color:   "#028090"
#         alpha:   0.85
#         figsize: [10, 5]

#     bar:
#       color_any:       "#028090"
#       color_multiple:  "#E05C40"
#       color_none:      "#EEEEEE"
#       show_pct_labels: true
#       alpha:           0.85
#       show_ci:         true
#       ci_alpha:        0.8
#       ci_color:        "#333333"
#     """
#     general:   GeneralConfig       = field(default_factory=GeneralConfig)
#     histogram: HistogramPlotConfig = field(default_factory=HistogramPlotConfig)
#     bar:       VolumeBarConfig     = field(default_factory=VolumeBarConfig)

#     _VALID_SECTIONS = {"general", "histogram", "bar"}

#     @classmethod
#     def _build_sections(cls, data: dict) -> dict:
#         cls._check_sections(data)
#         return {
#             "general":   _section(GeneralConfig, data.get("general")),
#             "histogram": _build_histogram(data.get("histogram")),
#             "bar":       _section(VolumeBarConfig, data.get("bar")),
#         }

#     def __repr__(self) -> str:
#         return (
#             f"OccurrenceResultVolumeConfig(\n"
#             f"  general   : title={self.general.title!r}, dpi={self.general.dpi}\n"
#             f"  histogram : bins={self.histogram.bins.type}, "
#             f"color={self.histogram.style.color}\n"
#             f"  bar       : color_any={self.bar.color_any}, "
#             f"color_multiple={self.bar.color_multiple}\n"
#             f")"
#         )


# # ── Timing config ─────────────────────────────────────────────────────────────

# @dataclass
# class SurvivalCurveConfig:
#     """
#     Visual settings for OccurrenceResultTimingPlotter.plot_survival().

#     Fields
#     ------
#     color : str
#         KM step curve color. Default '#028090'.
#     alpha : float
#         Curve line transparency. Default 0.9.
#     show_ci : bool
#         Draw Greenwood confidence interval band. Default True.
#     ci_alpha : float
#         CI band transparency. Default 0.2.
#     ci_color : str
#         CI band color. Default '#028090'.
#     show_censoring_marks : bool
#         Draw tick marks at censoring timepoints. Default True.
#     censoring_mark_color : str
#         Color for censoring tick marks. Default '#AAAAAA'.
#     """
#     color:                str   = "#028090"
#     alpha:                float = 0.9
#     show_ci:              bool  = True
#     ci_alpha:             float = 0.2
#     ci_color:             str   = "#028090"
#     show_censoring_marks: bool  = True
#     censoring_mark_color: str   = "#AAAAAA"

#     def __post_init__(self) -> None:
#         _hex(self.color,                "survival.color")
#         _hex(self.ci_color,             "survival.ci_color")
#         _hex(self.censoring_mark_color, "survival.censoring_mark_color")
#         _alpha(self.alpha,              "survival.alpha")
#         _alpha(self.ci_alpha,           "survival.ci_alpha")

#         if not self.show_ci and self.ci_alpha != 0.2:
#             warnings.warn(
#                 f"[{_PREFIX}] survival.show_ci=False but ci_alpha is set "
#                 "— it will be ignored.",
#                 UserWarning, stacklevel=2,
#             )
#         if not self.show_censoring_marks and self.censoring_mark_color != "#AAAAAA":
#             warnings.warn(
#                 f"[{_PREFIX}] survival.show_censoring_marks=False but "
#                 "censoring_mark_color is set — it will be ignored.",
#                 UserWarning, stacklevel=2,
#             )


# @dataclass
# class FacetConfig:
#     """
#     Facet layout settings for OccurrenceResultTimingPlotter.plot_histogram().

#     One subplot per nth occurrence. All subplots share the same x-axis
#     scale — auto-computed across all nths unless x-axis limits are set
#     on the histogram bins config.

#     Fields
#     ------
#     facet_height : float
#         Height in inches of each facet row. Default 3.0.
#     facet_width : float
#         Width in inches of each facet. Default 6.0.
#     """
#     facet_height: float = 3.0
#     facet_width:  float = 6.0

#     def __post_init__(self) -> None:
#         _pos(self.facet_height, "facet.facet_height")
#         _pos(self.facet_width,  "facet.facet_width")


# @dataclass
# class OccurrenceResultTimingConfig(_PlotterConfigBase):
#     """
#     Configuration for OccurrenceResultTimingPlotter.

#     Sections
#     --------
#     general         : GeneralConfig
#         Layout and style shared across all plots.
#     histogram       : HistogramPlotConfig
#         Applied to all nth histograms by default.
#     histogram_per_n : dict[int, HistogramPlotConfig]
#         Optional per-nth overrides. Only specify what differs from histogram —
#         section-level keys (bins, labels, style, ...) are merged on top of the
#         base; everything else is inherited.
#     facet           : FacetConfig
#         Controls subplot height and width for the faceted histogram.
#     survival        : SurvivalCurveConfig
#         Controls the KM curve appearance for plot_survival().

#     Usage
#     -----
#     >>> config = OccurrenceResultTimingConfig()
#     >>> config = OccurrenceResultTimingConfig.build_from_yaml("timing_config.yaml")
#     >>> config.to_yaml("timing_config.yaml")

#     Example YAML
#     ------------
#     general:
#       title:     null
#       dpi:       150
#       font_size: 11
#       style:     "seaborn-v0_8-whitegrid"

#     # Base histogram — applied to ALL nth facets unless overridden below.
#     histogram:
#       bins:
#         type:  fixed_width
#         width: 7
#         min:   0
#         max:   365
#       labels:
#         xlabel: "Days from observation start"
#         ylabel: "Entities"
#       style:
#         color:   "#028090"
#         alpha:   0.85
#         figsize: [10, 5]

#     # Per-nth overrides — only specify sections/fields that differ.
#     # nth=2 changes only style.color; all other fields come from histogram.
#     histogram_per_n:
#       2:
#         style:
#           color: "#E05C40"
#       3:
#         style:
#           color: "#6B4FA0"

#     facet:
#       facet_height: 3.0
#       facet_width:  6.0

#     survival:
#       color:                "#028090"
#       alpha:                0.9
#       show_ci:              true
#       ci_alpha:             0.2
#       ci_color:             "#028090"
#       show_censoring_marks: true
#       censoring_mark_color: "#AAAAAA"
#     """
#     general:         GeneralConfig                        = field(default_factory=GeneralConfig)
#     histogram:       HistogramPlotConfig                  = field(default_factory=HistogramPlotConfig)
#     histogram_per_n: dict[int, HistogramPlotConfig]       = field(default_factory=dict)
#     facet:           FacetConfig                          = field(default_factory=FacetConfig)
#     survival:        SurvivalCurveConfig                  = field(default_factory=SurvivalCurveConfig)

#     _VALID_SECTIONS = {"general", "histogram", "histogram_per_n", "facet", "survival"}

#     def resolve_histogram_for_nth(self, n: int) -> HistogramPlotConfig:
#         """
#         Return the HistogramPlotConfig for the nth occurrence.
#         Falls back to self.histogram if no per-nth override exists.
#         Per-nth configs are merged section-by-section on top of the base —
#         only sections/fields explicitly set in histogram_per_n differ.
#         """
#         return self.histogram_per_n.get(n, self.histogram)

#     @classmethod
#     def _build_sections(cls, data: dict) -> dict:
#         cls._check_sections(data)

#         base_histogram = _build_histogram(data.get("histogram"))

#         raw_per_n = data.get("histogram_per_n") or {}
#         if not isinstance(raw_per_n, dict):
#             raise _err(
#                 f"histogram_per_n must be a mapping of int → section overrides, "
#                 f"got {type(raw_per_n).__name__}"
#             )
#         histogram_per_n: dict[int, HistogramPlotConfig] = {}
#         for key, override in raw_per_n.items():
#             if not isinstance(key, int):
#                 raise _err(
#                     f"histogram_per_n keys must be integers, got {key!r}"
#                 )
#             if key < 1:
#                 raise _err(
#                     f"histogram_per_n keys must be >= 1, got {key}"
#                 )
#             histogram_per_n[key] = _merge_histogram(base_histogram, override)

#         return {
#             "general":         _section(GeneralConfig,       data.get("general")),
#             "histogram":       base_histogram,
#             "histogram_per_n": histogram_per_n,
#             "facet":           _section(FacetConfig,         data.get("facet")),
#             "survival":        _section(SurvivalCurveConfig, data.get("survival")),
#         }

#     def __repr__(self) -> str:
#         n_overrides = len(self.histogram_per_n)
#         return (
#             f"OccurrenceResultTimingConfig(\n"
#             f"  general         : title={self.general.title!r}, dpi={self.general.dpi}\n"
#             f"  histogram       : bins={self.histogram.bins.type}, "
#             f"color={self.histogram.style.color}\n"
#             f"  histogram_per_n : {n_overrides} override(s) — "
#             f"nths: {sorted(self.histogram_per_n.keys())}\n"
#             f"  facet           : {self.facet.facet_height}h x "
#             f"{self.facet.facet_width}w per subplot\n"
#             f"  survival        : color={self.survival.color}, "
#             f"show_ci={self.survival.show_ci}\n"
#             f")"
#         )


# # ── Shape config ──────────────────────────────────────────────────────────────

# @dataclass
# class ShapeScatterConfig:
#     """
#     Visual settings for OccurrenceResultShapePlotter.plot_fingerprint().

#     Fields
#     ------
#     color : str
#         Marker color. Default '#028090'.
#     alpha : float
#         Marker transparency. Default 0.7.
#     size : int
#         Marker size in points. Default 40.
#     show_grid : bool
#         Show background grid. Default True.
#     show_quadrant_lines : bool
#         Draw reference lines at burstiness=0 and memory=0. Default True.
#     quadrant_line_color : str
#         Color for quadrant reference lines. Default '#AAAAAA'.
#     """
#     color:               str   = "#028090"
#     alpha:               float = 0.7
#     size:                int   = 40
#     show_grid:           bool  = True
#     show_quadrant_lines: bool  = True
#     quadrant_line_color: str   = "#AAAAAA"

#     def __post_init__(self) -> None:
#         _hex(self.color,               "scatter.color")
#         _hex(self.quadrant_line_color, "scatter.quadrant_line_color")
#         _alpha(self.alpha,             "scatter.alpha")
#         _pos(self.size,                "scatter.size")

#         if not self.show_quadrant_lines and self.quadrant_line_color != "#AAAAAA":
#             warnings.warn(
#                 f"[{_PREFIX}] scatter.show_quadrant_lines=False but "
#                 "quadrant_line_color is set — it will be ignored.",
#                 UserWarning, stacklevel=2,
#             )


# @dataclass
# class OccurrenceResultShapeConfig(_PlotterConfigBase):
#     """
#     Configuration for OccurrenceResultShapePlotter.

#     Sections
#     --------
#     general        : GeneralConfig
#         Layout and style shared across all shape plots.
#     center_of_mass : HistogramPlotConfig
#         For plot_center_of_mass(). x range defaults to [0, 1].
#     density        : HistogramPlotConfig
#         For plot_density(). x range defaults to auto.
#     scatter        : ShapeScatterConfig
#         For plot_fingerprint() — burstiness vs memory scatter.

#     Usage
#     -----
#     >>> config = OccurrenceResultShapeConfig()
#     >>> config = OccurrenceResultShapeConfig.build_from_yaml("shape_config.yaml")
#     >>> config.to_yaml("shape_config.yaml")

#     Example YAML
#     ------------
#     general:
#       title:     null
#       dpi:       150
#       font_size: 11
#       style:     "seaborn-v0_8-whitegrid"

#     # center_of_mass is normalized to [0, 1]. 0=front-loaded, 1=back-loaded.
#     center_of_mass:
#       bins:
#         type:  fixed_width
#         width: 0.05
#         min:   0.0
#         max:   1.0
#       labels:
#         xlabel: "Center of mass (0=front-loaded, 1=back-loaded)"
#         ylabel: "Entities"
#       style:
#         color: "#028090"

#     # density = n / obs_duration_days. max null = auto from data.
#     density:
#       bins:
#         type:  fixed_width
#         width: 0.1
#         min:   0.0
#       labels:
#         xlabel: "Density (occurrences per day)"
#         ylabel: "Entities"
#       style:
#         color: "#6B4FA0"

#     # Quadrant lines divide into four behavioral regions:
#     #   top-right    — bursty + persistent
#     #   bottom-right — bursty + alternating
#     #   top-left     — regular + persistent
#     #   bottom-left  — regular + alternating (most common)
#     scatter:
#       color:               "#028090"
#       alpha:               0.7
#       size:                40
#       show_grid:           true
#       show_quadrant_lines: true
#       quadrant_line_color: "#AAAAAA"
#     """
#     general:        GeneralConfig       = field(default_factory=GeneralConfig)
#     center_of_mass: HistogramPlotConfig = field(
#         default_factory=lambda: HistogramPlotConfig(
#             bins   = BinsConfig(type="fixed_width", width=0.05, min=0.0, max=1.0),
#             labels = LabelsConfig(
#                 xlabel="Center of mass (0=front-loaded, 1=back-loaded)",
#                 ylabel="Entities",
#             ),
#             style  = StyleConfig(color="#028090"),
#         )
#     )
#     density:        HistogramPlotConfig = field(
#         default_factory=lambda: HistogramPlotConfig(
#             bins   = BinsConfig(type="fixed_width", width=0.1, min=0.0),
#             labels = LabelsConfig(
#                 xlabel="Density (occurrences per day)",
#                 ylabel="Entities",
#             ),
#             style  = StyleConfig(color="#6B4FA0"),
#         )
#     )
#     scatter:        ShapeScatterConfig  = field(default_factory=ShapeScatterConfig)

#     _VALID_SECTIONS = {"general", "center_of_mass", "density", "scatter"}

#     @classmethod
#     def _build_sections(cls, data: dict) -> dict:
#         cls._check_sections(data)
#         return {
#             "general":        _section(GeneralConfig,      data.get("general")),
#             "center_of_mass": _build_histogram(data.get("center_of_mass")),
#             "density":        _build_histogram(data.get("density")),
#             "scatter":        _section(ShapeScatterConfig, data.get("scatter")),
#         }

#     def __repr__(self) -> str:
#         return (
#             f"OccurrenceResultShapeConfig(\n"
#             f"  general        : title={self.general.title!r}, dpi={self.general.dpi}\n"
#             f"  center_of_mass : bins={self.center_of_mass.bins.type}, "
#             f"color={self.center_of_mass.style.color}\n"
#             f"  density        : bins={self.density.bins.type}, "
#             f"color={self.density.style.color}\n"
#             f"  scatter        : color={self.scatter.color}, "
#             f"alpha={self.scatter.alpha}, size={self.scatter.size}\n"
#             f")"
#         )
