"""
event_co_occurrence_gap_plot_config.py
EventCoOccurrenceGapPlotConfig — configuration for
EventCoOccurrenceGapPlotter.

Simple config: canvas size, colors, KDE bandwidth.
All parameters have defaults so the plotter works with zero config.
"""
from __future__ import annotations

_ERROR = "[EventCoOccurrenceGapPlotConfig] Error"

_DEFAULTS = {
    "figsize":          (10, 8),
    "dpi":              120,
    "color_observed":   "#028090",   # teal — observed gaps
    "color_null":       "#E05C40",   # coral — permutation null
    "alpha_observed":   0.7,
    "alpha_null":       0.4,
    "bandwidth":        "scott",
    "show_medians":     True,
    "show_ks":          True,
    "font_size":        12,
}


class EventCoOccurrenceGapPlotConfig:
    """
    Configuration for EventCoOccurrenceGapPlotter.

    Parameters
    ----------
    figsize        : tuple (width, height) in inches. Default (10, 8).
    dpi            : int. Default 120.
    color_observed : hex string. Color for observed gap KDE. Default teal.
    color_null     : hex string. Color for null gap KDE. Default coral.
    alpha_observed : float in [0, 1]. Opacity for observed fill. Default 0.7.
    alpha_null     : float in [0, 1]. Opacity for null fill. Default 0.4.
    bandwidth      : KDE bandwidth. 'scott', 'silverman', or float. Default 'scott'.
    show_medians   : bool. Draw vertical lines at observed and null medians. Default True.
    show_ks        : bool. Annotate KS statistic and p-value on plot. Default True.
    font_size      : int. Base font size. Default 12.

    All parameters are optional — defaults produce a publication-ready figure.

    Examples
    --------
    >>> # Use all defaults
    >>> config = EventCoOccurrenceGapPlotConfig()

    >>> # Custom colors and bandwidth
    >>> config = EventCoOccurrenceGapPlotConfig(
    ...     color_observed = "#3A86FF",
    ...     color_null     = "#FF006E",
    ...     bandwidth      = "silverman",
    ... )
    """

    def __init__(
        self,
        figsize:        tuple      = _DEFAULTS["figsize"],
        dpi:            int        = _DEFAULTS["dpi"],
        color_observed: str        = _DEFAULTS["color_observed"],
        color_null:     str        = _DEFAULTS["color_null"],
        alpha_observed: float      = _DEFAULTS["alpha_observed"],
        alpha_null:     float      = _DEFAULTS["alpha_null"],
        bandwidth                    = _DEFAULTS["bandwidth"],
        show_medians:   bool       = _DEFAULTS["show_medians"],
        show_ks:        bool       = _DEFAULTS["show_ks"],
        font_size:      int        = _DEFAULTS["font_size"],
    ) -> None:
        self.figsize        = figsize
        self.dpi            = dpi
        self.color_observed = color_observed
        self.color_null     = color_null
        self.alpha_observed = alpha_observed
        self.alpha_null     = alpha_null
        self.bandwidth      = bandwidth
        self.show_medians   = show_medians
        self.show_ks        = show_ks
        self.font_size      = font_size

    @classmethod
    def defaults(cls) -> "EventCoOccurrenceGapPlotConfig":
        """Return a config with all default values."""
        return cls()

    def __repr__(self) -> str:
        return (
            f"EventCoOccurrenceGapPlotConfig(\n"
            f"  figsize        : {self.figsize}\n"
            f"  dpi            : {self.dpi}\n"
            f"  color_observed : {self.color_observed}\n"
            f"  color_null     : {self.color_null}\n"
            f"  bandwidth      : {self.bandwidth}\n"
            f"  show_medians   : {self.show_medians}\n"
            f"  show_ks        : {self.show_ks}\n"
            f")"
        )
