import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import eventus.visualizers.configs.plot_config_utils as plot_utils

_VALID_LINESTYLES   = {"dashed", "dotted", "solid"}

@dataclass
class PercentilesConfig:
    """Vertical reference lines drawn at chosen percentiles."""
    show:        bool      = True
    values:      list[int] = field(default_factory=lambda: [25, 50, 75, 90])
    color:       str       = "#333333"
    linestyle:   str       = "dashed"
    show_labels: bool      = True

    _PREFIX = "PercentilesConfig"

    def __post_init__(self) -> None:
        plot_utils.validate_hex(self.color, "percentile_lines.color", self._PREFIX)
        plot_utils.validate_choice(self.linestyle, _VALID_LINESTYLES,"percentile_lines.linestyle", self._PREFIX)
        bad = [v for v in self.values if not (0 <= v <= 100)]
        if bad:
            raise plot_utils.err(self._PREFIX, f"percentile_lines.values must be between 0 and 100, got {bad}")
        if not self.show and (self.values or self.show_labels):
            warnings.warn(
                f"[{self._PREFIX}] percentile_lines.show=False but values/labels "
                "are configured — they will be ignored.",
                UserWarning, stacklevel=2,
            )
