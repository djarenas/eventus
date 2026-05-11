"""
percentiles_config.py
Vertical reference lines drawn at chosen percentiles of the data.
Used by histogram and violin plot configs.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import ClassVar

from eventus.visualizers.configs.plot_config_utils import (
    err,
    validate_choice,
    validate_hex,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_PREFIX             = "percentile lines"
_VALID_LINESTYLES   = {"dashed", "dotted", "solid"}


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class PercentilesConfig:
    """
    Vertical reference lines drawn at chosen percentiles of the data.

    Fields
    ------
    show        : Draw percentile lines. If False, all other fields are ignored.
    values      : Percentile values to mark. Must be in [0, 100].
    color       : Line color.
    linestyle   : Line style — 'dashed', 'dotted', or 'solid'.
    show_labels : Annotate each line with its percentile label.
                  Ignored if show=False.
    """
    show:        bool      = True
    values:      list[int] = field(default_factory=lambda: [25, 50, 75, 90])
    color:       str       = "#333333"
    linestyle:   str       = "dashed"
    show_labels: bool      = True

    _PREFIX: ClassVar[str] = _PREFIX

    def __post_init__(self) -> None:
        validate_hex(self.color, "color", self._PREFIX)
        validate_choice(self.linestyle, _VALID_LINESTYLES, "linestyle", self._PREFIX)

        bad = [v for v in self.values if not (0 <= v <= 100)]
        if bad:
            raise err(self._PREFIX, f"values must be in [0, 100], got {bad}")

        if not self.show:
            warnings.warn(
                f"[{self._PREFIX}] show=False — values, color, linestyle, "
                "and show_labels will be ignored.",
                UserWarning, stacklevel=2,
            )
