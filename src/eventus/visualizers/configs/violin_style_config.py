"""
violin_style_config.py

Shared style configuration dataclasses for violin plots in eventus.

    ViolinAxisConfig  — axis tick control + optional y bounds
    ViolinStyleConfig — bandwidth, box, point display settings

Used by:
    ArraysViolinConfig  (arrays_violin_config.py)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from eventus.visualizers.configs.base_plot_config import AxisConfig
from eventus.visualizers.configs.plot_config_utils import (
    err,
    validate_alpha,
    validate_choice,
    validate_float,
    validate_positive_float,
    validate_positive_integer,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_VALID_BW = {"scott", "silverman"}


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ViolinAxisConfig(AxisConfig):
    """
    Axis configuration for violin plots.
    Extends AxisConfig with optional y-axis bounds.
    """
    # --- Inherited from AxisConfig ---
    # x_ticks:         list[float] | None
    # y_ticks:         list[float] | None
    # x_tick_rotation: float
    # y_tick_rotation: float
    # x_tick_format:   str | None
    # y_tick_format:   str | None
    # tick_font_size:  int | None

    y_min: float | None = None
    y_max: float | None = None

    _PREFIX: ClassVar[str] = "ViolinAxisConfig"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.y_min is not None:
            self.y_min = validate_float(self.y_min, self._PREFIX, "y_min")
        if self.y_max is not None:
            self.y_max = validate_float(self.y_max, self._PREFIX, "y_max")
        if self.y_min is not None and self.y_max is not None:
            if self.y_min >= self.y_max:
                raise err(
                    self._PREFIX,
                    f"y_min ({self.y_min}) must be less than y_max ({self.y_max})",
                )


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
        self.point_alpha    = validate_alpha(self.point_alpha,           self._PREFIX, "point_alpha")
        self.point_size     = validate_positive_float(self.point_size,   self._PREFIX, "point_size")
        self.max_categories = validate_positive_integer(self.max_categories, self._PREFIX, "max_categories")
        if self.max_categories < 1:
            raise err(self._PREFIX, f"style.max_categories must be >= 1, got {self.max_categories}")
