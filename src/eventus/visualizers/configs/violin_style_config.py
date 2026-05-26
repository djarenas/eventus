"""
violin_style_config.py

Shared style configuration dataclass for violin plots in eventus.

    ViolinStyleConfig — bandwidth, box, point display settings

ViolinAxisConfig lives in violin_axis_config.py and is imported
by both this module and violin_config.py.

Used by:
    ArraysViolinConfig        (arrays_violin_config.py)
    BaseViolinConfig          (violin_config.py)
    EpisodeDurationViolinConfig (violin_config.py)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from eventus.visualizers.configs.plot_config_utils import (
    err,
    validate_alpha,
    validate_choice,
    validate_positive_float,
    validate_positive_integer,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_VALID_BW = {"scott", "silverman"}


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class ViolinStyleConfig:
    """Visual style settings for violin plots."""
    bandwidth:      str   = "scott"
    show_box:       bool  = True
    show_points:    bool  = False
    point_alpha:    float = 0.3
    point_size:     float = 3.0
    max_categories: int   = 8

    _PREFIX: ClassVar[str] = "ViolinStyleConfig"

    def __post_init__(self) -> None:
        validate_choice(self.bandwidth, _VALID_BW, "style.bandwidth", self._PREFIX)
        self.point_alpha    = validate_alpha(self.point_alpha,               self._PREFIX, "point_alpha")
        self.point_size     = validate_positive_float(self.point_size,       self._PREFIX, "point_size")
        self.max_categories = validate_positive_integer(self.max_categories, self._PREFIX, "max_categories")
        if self.max_categories < 1:
            raise err(self._PREFIX, f"style.max_categories must be >= 1, got {self.max_categories}")
