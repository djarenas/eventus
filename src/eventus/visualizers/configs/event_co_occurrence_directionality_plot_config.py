"""
event_co_occurrence_directionality_plot_config.py
Config for EventCoOccurrenceDirectionalityPlotter.
"""
from __future__ import annotations

_DEFAULTS = {
    "figsize":        (10, 5),
    "dpi":            120,
    "color_observed": "#028090",
    "color_null":     "#E05C40",
    "alpha_observed": 0.7,
    "alpha_null":     0.4,
    "bandwidth":      "scott",
    "show_zero_line": True,
    "show_means":     True,
    "font_size":      12,
}


class EventCoOccurrenceDirectionalityPlotConfig:
    """
    Configuration for EventCoOccurrenceDirectionalityPlotter.

    All parameters optional — defaults produce a publication-ready figure.

    Parameters
    ----------
    figsize        : tuple. Default (10, 5).
    dpi            : int. Default 120.
    color_observed : hex. Teal by default.
    color_null     : hex. Coral by default.
    alpha_observed : float. Default 0.7.
    alpha_null     : float. Default 0.4.
    bandwidth      : KDE bandwidth. Default 'scott'.
    show_zero_line : bool. Draw vertical line at zero. Default True.
    show_means     : bool. Draw vertical lines at observed/null means. Default True.
    font_size      : int. Default 12.
    """

    def __init__(
        self,
        figsize        = _DEFAULTS["figsize"],
        dpi            = _DEFAULTS["dpi"],
        color_observed = _DEFAULTS["color_observed"],
        color_null     = _DEFAULTS["color_null"],
        alpha_observed = _DEFAULTS["alpha_observed"],
        alpha_null     = _DEFAULTS["alpha_null"],
        bandwidth      = _DEFAULTS["bandwidth"],
        show_zero_line = _DEFAULTS["show_zero_line"],
        show_means     = _DEFAULTS["show_means"],
        font_size      = _DEFAULTS["font_size"],
    ) -> None:
        self.figsize        = figsize
        self.dpi            = dpi
        self.color_observed = color_observed
        self.color_null     = color_null
        self.alpha_observed = alpha_observed
        self.alpha_null     = alpha_null
        self.bandwidth      = bandwidth
        self.show_zero_line = show_zero_line
        self.show_means     = show_means
        self.font_size      = font_size

    @classmethod
    def defaults(cls) -> "EventCoOccurrenceDirectionalityPlotConfig":
        return cls()
