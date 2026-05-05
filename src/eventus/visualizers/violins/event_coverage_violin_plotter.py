"""
event_coverage_violin_plotter.py
EventCoverageViolinPlotter — violin plots from a CohortTimeline with
event coverage analysis columns.

Two plot methods:
  plot_total()              — evt_{identity}_active_days vs inactive_days
  plot_inactive_breakdown() — inactive metrics, filtered to > 0
"""
from __future__ import annotations
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.cohort_timeline.cohort_timeline import CohortTimeline
from .event_coverage_violin_config import EventCoverageViolinConfig

_ERROR_PREFIX = "[EventCoverageViolinPlotter] Error"


def _required_analysis_cols(identity: str) -> set[str]:
    """Return the set of required analysis column names for a given identity."""
    p = f"evt_{identity}_"
    return {
        "obs_duration_days",
        f"{p}active_days",
        f"{p}inactive_days",
        f"{p}inactive_days_before_first_event",
        f"{p}inactive_days_after_last_event",
        f"{p}inactive_days_middle",
        f"{p}first_start",
        f"{p}last_end",
    }


class EventCoverageViolinPlotter:
    """
    Violin plots from a CohortTimeline with event coverage analysis columns.

    The CohortTimeline must already have analysis columns for the given
    identity — produced by CohortTimelineEventAnalyzer.compute_coverage().

    Parameters
    ----------
    cohort_timeline : CohortTimeline
        Must have evt_{identity}_active_days and related analysis columns
        present. Call CohortTimelineEventAnalyzer(ct, identity).compute_coverage()
        first if they are not yet present.
    config : EventCoverageViolinConfig
        Plot configuration. config.identity determines which event identity's
        analysis columns are expected in the CohortTimeline.

    Examples
    --------
    >>> ct = CohortTimelineEventAnalyzer(ct, "inpatient_hospitalization").compute_coverage()
    >>> config  = EventCoverageViolinConfig.build_with_defaults("inpatient_hospitalization")
    >>> plotter = EventCoverageViolinPlotter(ct, config)
    >>> plotter.plot_total("active_vs_inactive.png")
    >>> plotter.plot_inactive_breakdown("inactive_breakdown.png")
    """

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        config:          EventCoverageViolinConfig,
    ) -> None:
        if not isinstance(config, EventCoverageViolinConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an EventCoverageViolinConfig, "
                f"got {type(config).__name__}"
            )
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR_PREFIX}: cohort_timeline must be a CohortTimeline "
                f"object, got {type(cohort_timeline).__name__}"
            )

        identity = config.identity
        required = _required_analysis_cols(identity)
        missing  = required - set(cohort_timeline.data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: cohort_timeline is missing analysis columns "
                f"for identity '{identity}': {sorted(missing)}. "
                f"Call CohortTimelineEventAnalyzer(ct, '{identity}').compute_coverage() first."
            )

        self._cohort_timeline = cohort_timeline
        self._config          = config
        self._identity        = identity
        self._n_total         = len(cohort_timeline)

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_total(self, path: str) -> None:
        """
        Two-violin plot: evt_{identity}_active_days vs
        evt_{identity}_inactive_days. Both include ALL entities.

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

        from .event_coverage_violin_plotter_utils import build_total_arrays

        plot_order, arrays = build_total_arrays(
            self._cohort_timeline.data, self._identity
        )

        self._draw(
            path       = path,
            arrays     = arrays,
            plot_order = plot_order,
            title      = f"Active vs Inactive days — {self._identity}",
        )

    def plot_inactive_breakdown(self, path: str) -> None:
        """
        Up to four violin plots showing the inactive day breakdown.
        Each violin filtered to entities where that metric > 0.

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

        from .event_coverage_violin_plotter_utils import build_breakdown_arrays

        plot_order, arrays = build_breakdown_arrays(
            data           = self._cohort_timeline.data,
            identity       = self._identity,
            breakdown_cols = self._config.breakdown_cols,
        )

        self._draw(
            path       = path,
            arrays     = arrays,
            plot_order = plot_order,
            title      = f"Inactive day breakdown — {self._identity}",
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
        from .event_coverage_violin_plotter_utils import (
            compute_widths, draw_violins,
            build_tick_labels, apply_unit_conversion,
        )

        cfg  = self._config
        scfg = cfg.style
        pcfg = cfg.percentiles
        lcfg = cfg.labels

        # plot_order and arrays are keyed by short metric names —
        # direct lookup into cfg.metrics with no string manipulation needed.
        arrays = apply_unit_conversion(arrays, lcfg.divisor)
        widths = compute_widths(arrays, plot_order)
        colors = {key: cfg.metrics[key].color for key in plot_order}

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

        tick_labels = build_tick_labels(
            plot_order = plot_order,
            arrays     = arrays,
            n_total    = self._n_total,
            config     = cfg,
        )
        ax.set_xticks(range(len(plot_order)))
        ax.set_xticklabels(tick_labels, fontsize=9)
        ax.set_xlim(-0.5, len(plot_order) - 0.5)

        ax.set_title(lcfg.title or title, fontsize=12)
        ax.set_ylabel(lcfg.resolved_ylabel, fontsize=10)
        ax.tick_params(axis="y", labelsize=9)

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
            f"EventCoverageViolinPlotter(\n"
            f"  identity    : {self._identity!r}\n"
            f"  entities    : {self._n_total:,}\n"
            f"  metrics     : {list(self._config.metrics.keys())}\n"
            f")"
        )
