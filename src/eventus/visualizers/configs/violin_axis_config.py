"""
violin_axis_config.py
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, ClassVar

from eventus.visualizers.configs.base_plot_config import AxisConfig
from eventus.visualizers.configs.plot_config_utils import (
    err,
    validate_float,
)



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
