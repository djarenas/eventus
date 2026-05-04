"""
events_within_obs_period_violin_plotter.py
EventsWithinObsPeriodViolinPlotter — violin plots from
PipeDelimitedIntermediateEvents.

Two plot methods:
  plot_total()              — active_days vs inactive_days, full cohort
  plot_inactive_breakdown() — inactive metrics, filtered to > 0
"""
from __future__ import annotations
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ERROR_PREFIX = "[EventsWithinObsPeriodViolinPlotter] Error"

_ANALYSIS_COLS = {
    "span_duration_days",
    "active_days",
    "inactive_days",
    "inactive_days_before_first_event",
    "inactive_days_after_last_event",
    "inactive_days_middle",
    "first_event_start",
    "last_event_end",
}


class EventsWithinObsPeriodViolinPlotter:
    """
    Violin plots from a PipeDelimitedIntermediateEvents object.

    Parameters
    ----------
    intermediate : PipeDelimitedIntermediateEvents
        Must have analysis columns present — produced by
        EventsWithinObsPeriodsAnalyzer.compute_event_coverage().
    config : EventsWithinObsPeriodViolinConfig
        Plot configuration.

    Examples
    --------
    >>> config  = EventsWithinObsPeriodViolinConfig.build_from_yaml("config.yaml")
    >>> plotter = EventsWithinObsPeriodViolinPlotter(intermediate, config)
    >>> plotter.plot_total("active_vs_inactive.png")
    >>> plotter.plot_inactive_breakdown("inactive_breakdown.png")
    """

    def __init__(self, intermediate, config) -> None:
        from .events_within_obs_period_violin_config import (
            EventsWithinObsPeriodViolinConfig
        )

        if not isinstance(config, EventsWithinObsPeriodViolinConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an "
                f"EventsWithinObsPeriodViolinConfig, "
                f"got {type(config).__name__}"
            )

        missing = _ANALYSIS_COLS - set(intermediate.data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: intermediate is missing analysis columns: "
                f"{sorted(missing)}. "
                f"Make sure you used EventsWithinObsPeriodsAnalyzer"
                f".compute_event_coverage() to build this intermediate."
            )

        self._intermediate = intermediate
        self._config       = config
        self._n_total      = len(intermediate.data)

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_total(self, path: str) -> None:
        """
        Two-violin plot: active_days vs inactive_days.

        Both violins include ALL entities — zero is valid and meaningful.
        Width is equal since both use the full cohort.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        self._validate_path(path)

        if not self._config.can_plot_total():
            raise ValueError(
                f"{_ERROR_PREFIX}: plot_total() requires both 'active_days' "
                f"and 'inactive_days' in the metrics config."
            )

        from .events_within_obs_period_violin_plotter_utils import (
            build_total_arrays
        )

        plot_order, arrays = build_total_arrays(self._intermediate.data)

        self._draw(
            path       = path,
            arrays     = arrays,
            plot_order = plot_order,
            title      = f"Active vs Inactive days — {self._config.identity}",
        )

    def plot_inactive_breakdown(self, path: str) -> None:
        """
        Up to four violin plots showing the inactive day breakdown.

        Each violin filtered to entities where that metric > 0:
        - inactive_days                    — any inactive time
        - inactive_days_before_first_event
        - inactive_days_after_last_event
        - inactive_days_middle             — gaps between events (≥ 2 events)

        Width proportional to n — visually communicates what fraction
        of the cohort each type of inactivity applies to.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        self._validate_path(path)

        if not self._config.can_plot_breakdown():
            raise ValueError(
                f"{_ERROR_PREFIX}: plot_inactive_breakdown() requires at "
                f"least one of: inactive_days_before_first_event, "
                f"inactive_days_after_last_event, inactive_days_middle "
                f"in the metrics config."
            )

        from .events_within_obs_period_violin_plotter_utils import (
            build_breakdown_arrays
        )

        plot_order, arrays = build_breakdown_arrays(
            data            = self._intermediate.data,
            breakdown_cols  = self._config.breakdown_cols,
        )

        self._draw(
            path       = path,
            arrays     = arrays,
            plot_order = plot_order,
            title      = f"Inactive day breakdown — {self._config.identity}",
        )

    # ------------------------------------------------------------------ #
    # Shared drawing logic
    # ------------------------------------------------------------------ #

    def _draw(
        self,
        path:       str,
        arrays:     dict[str, np.ndarray],
        plot_order: list[str],
        title:      str,
    ) -> None:
        """Shared rendering for both plot methods."""
        from .events_within_obs_period_violin_plotter_utils import (
            compute_widths, draw_violins,
            build_tick_labels, apply_unit_conversion,
        )

        cfg  = self._config
        scfg = cfg.style
        pcfg = cfg.percentiles
        lcfg = cfg.labels

        # Apply duration unit conversion
        arrays = apply_unit_conversion(arrays, lcfg.divisor)

        # Compute widths — proportional to n
        widths = compute_widths(arrays, plot_order)

        # Build colors dict
        colors = {
            col: cfg.metrics[col].color
            for col in plot_order
            if col in cfg.metrics
        }

        # Figure
        fig, ax = plt.subplots(figsize=scfg.figsize)

        draw_violins(
            ax          = ax,
            plot_order  = plot_order,
            arrays      = arrays,
            widths      = widths,
            colors      = colors,
            show_box    = scfg.show_box,
            show_points = scfg.show_points,
            point_alpha = scfg.point_alpha,
            point_size  = scfg.point_size,
            pcfg        = pcfg,
        )

        # X tick labels with n and % of cohort
        tick_labels = build_tick_labels(
            plot_order = plot_order,
            arrays     = arrays,
            n_total    = self._n_total,
            config     = cfg,
        )
        ax.set_xticks(range(len(plot_order)))
        ax.set_xticklabels(tick_labels, fontsize=9)
        ax.set_xlim(-0.5, len(plot_order) - 0.5)

        # Labels
        ax.set_title(lcfg.title or title, fontsize=12)
        ax.set_ylabel(lcfg.resolved_ylabel, fontsize=10)
        ax.tick_params(axis="y", labelsize=9)

        # Y axis bounds
        if scfg.y_min is not None or scfg.y_max is not None:
            ax.set_ylim(bottom=scfg.y_min, top=scfg.y_max)

        fig.tight_layout()
        fig.savefig(path, dpi=scfg.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Validation and dunder
    # ------------------------------------------------------------------ #

    def _validate_path(self, path: str) -> None:
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
                f"Use .png, .jpg, or .jpeg"
            )

    def __repr__(self) -> str:
        return (
            f"EventsWithinObsPeriodViolinPlotter(\n"
            f"  identity    : {self._config.identity!r}\n"
            f"  entities    : {self._n_total:,}\n"
            f"  metrics     : {list(self._config.metrics.keys())}\n"
            f")"
        )
