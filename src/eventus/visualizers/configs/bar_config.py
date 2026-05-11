"""
bar_config.py

Bar chart configuration classes for eventus visualizers.

Classes
-------
BaseBarConfig              — shared CI fields and warning; base for all bar configs
CategoryBarConfig          — fixed-category bar chart with per-category colors,
                             labels, and optional percentage labels
CountDistributionBarConfig — discrete integer count distribution bar chart with
                             overflow bucket, labels, and percentage/count toggle

Intended use
------------
CategoryBarConfig covers any bar chart where the categories are known upfront
and each has its own color — e.g. prevalence breakdowns, quadrant distributions.

CountDistributionBarConfig covers bar charts where the x-axis is a discrete
integer count (n=0, n=1, ... n=max_n+) — e.g. occurrence count distributions.

Future additions (e.g. SummaryBarConfig for single-series numeric bars) should
also inherit BaseBarConfig and call super().__post_init__() first.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import ClassVar

from eventus.visualizers.configs.base_plot_config import AxisLabels
from eventus.visualizers.configs.percentiles_config import PercentilesConfig
from eventus.visualizers.configs.plot_config_utils import (
    err,
    validate_alpha,
    validate_hex,
    validate_positive_integer,
)


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass
class BaseBarConfig:
    """
    Shared fields for all bar chart configs.

    Fields
    ------
    alpha    : Bar transparency. Range [0, 1].
    show_ci  : Draw confidence interval error bars.
    ci_alpha : CI error bar transparency. Ignored if show_ci=False.
    ci_color : CI error bar color. Ignored if show_ci=False.
    """
    alpha:    float = 0.85
    show_ci:  bool  = True
    ci_alpha: float = 0.8
    ci_color: str   = "#333333"

    _PREFIX: ClassVar[str] = "bar"

    def __post_init__(self) -> None:
        validate_alpha(self.alpha,    self._PREFIX, "alpha")
        validate_alpha(self.ci_alpha, self._PREFIX, "ci_alpha")
        validate_hex(self.ci_color, "ci_color", self._PREFIX)

        if not self.show_ci:
            warnings.warn(
                f"[{self._PREFIX}] show_ci=False — ci_alpha and ci_color will be ignored.",
                UserWarning, stacklevel=2,
            )


# ── Category bar ──────────────────────────────────────────────────────────────

@dataclass
class CategoryBarConfig(BaseBarConfig):
    """
    Bar chart with a fixed set of named categories, each with its own color.

    Covers any plot where the categories are known upfront — e.g. prevalence
    breakdowns (any / multiple / none), quadrant distributions, and similar.

    Fields (beyond BaseBarConfig)
    ------------------------------
    labels          : Title, subtitle, axis labels and units for this plot.
    color_any       : Bar color for the primary / 'any' category.
    color_multiple  : Bar color for the secondary / 'multiple' category.
    color_none      : Bar color for the absence / 'none' category.
    show_pct_labels : Annotate each bar with its percentage and count.

    Inherited from BaseBarConfig
    ----------------------------
    alpha    : Bar transparency.
    show_ci  : Draw confidence interval error bars.
    ci_alpha : CI transparency. Ignored if show_ci=False.
    ci_color : CI color. Ignored if show_ci=False.
    """
    labels:          AxisLabels = field(default_factory=AxisLabels)
    color_any:       str        = "#028090"
    color_multiple:  str        = "#E05C40"
    color_none:      str        = "#EEEEEE"
    show_pct_labels: bool       = True

    _PREFIX: ClassVar[str] = "category bar"

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_hex(self.color_any,      "color_any",      self._PREFIX)
        validate_hex(self.color_multiple, "color_multiple", self._PREFIX)
        validate_hex(self.color_none,     "color_none",     self._PREFIX)


# ── Count distribution bar ────────────────────────────────────────────────────

@dataclass
class CountDistributionBarConfig(BaseBarConfig):
    """
    Bar chart showing a discrete integer count distribution with an overflow bucket.

    Renders one bar per integer value from n=0 up to max_n-1, then a final
    overflow bar labeled 'n=max_n+' for all entities with n >= max_n.

    Percentile lines are drawn as vertical lines snapped to the nearest bar,
    computed from the raw n column. Because the x-axis is categorical, lines
    are positioned at bar centres rather than float x values.

    Fields (beyond BaseBarConfig)
    ------------------------------
    labels            : Title, subtitle, axis labels and units for this plot.
    max_n             : Overflow cutoff. Entities with n >= max_n are grouped
                        into a single 'n=max_n+' bar. Must be >= 2.
    color             : Bar fill color. All bars share one color.
    show_as_pct       : If True (default), y-axis shows % of cohort.
                        If False, y-axis shows raw entity counts.
    show_count_labels : Annotate each bar with percentage and raw count.
    percentile_lines  : Vertical reference lines at chosen percentiles of the
                        raw n distribution, snapped to the nearest bar position.

    Inherited from BaseBarConfig
    ----------------------------
    alpha    : Bar transparency.
    show_ci  : Draw Wilson confidence interval error bars.
    ci_alpha : CI transparency. Ignored if show_ci=False.
    ci_color : CI color. Ignored if show_ci=False.
    """
    labels:            AxisLabels        = field(default_factory=AxisLabels)
    max_n:             int               = 5
    color:             str               = "#028090"
    show_as_pct:       bool              = True
    show_count_labels: bool              = True
    percentile_lines:  PercentilesConfig = field(default_factory=PercentilesConfig)

    _PREFIX: ClassVar[str] = "count distribution bar"

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_hex(self.color, "color", self._PREFIX)
        self.max_n = validate_positive_integer(self.max_n, self._PREFIX, "max_n")
        if self.max_n < 2:
            raise err(self._PREFIX, f"max_n must be >= 2, got {self.max_n}")
        if not isinstance(self.percentile_lines, PercentilesConfig):
            raise err(
                self._PREFIX,
                f"percentile_lines must be a PercentilesConfig, "
                f"got {type(self.percentile_lines).__name__}",
            )
