"""
activity_over_time_plotter.py
ActivityOverTimePlotter — visualize cohort activity over time.

Two panels:
  Top    — line chart of fraction of entities active at each timepoint
  Bottom — diverging bar chart of entities entering and exiting

Takes an EventActivityOverTime result object produced by
CohortTimelineEventAnalyzer.compute_activity_over_time().
"""
from __future__ import annotations
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.visualizers.configs.activity_over_time_config import ActivityOverTimeConfig
from eventus.intermediates.event_activity_over_time import EventActivityOverTime

_ERROR_PREFIX = "[ActivityOverTimePlotter] Error"


class ActivityOverTimePlotter:
    """
    I visualize event-activity of a cohort over an observation period.

    Takes an EventActivityOverTime result object — produced by
    CohortTimelineEventAnalyzer.compute_activity_over_time() — and
    renders it as a two-panel plot.

    Top panel shows what fraction of the cohort is active at each timepoint.
    Bottom panel shows a diverging bar chart of entries and exits.

    Parameters
    ----------
    activity : EventActivityOverTime
        Validated timeseries result from compute_activity_over_time().
    config : ActivityOverTimeConfig | None
        Plot configuration. Uses ActivityOverTimeConfig() defaults
        if not provided.

    Examples
    --------
    >>> ct       = CohortTimelineEventAnalyzer(ct, "insurance_coverage").compute_coverage()
    >>> activity = analyzer.compute_activity_over_time(granularity="month", mode="calendar")
    >>> plotter  = ActivityOverTimePlotter(activity)
    >>> plotter.plot("activity.png")
    """

    def __init__(
        self,
        activity: EventActivityOverTime,
        config    = None,
    ) -> None:
        if not isinstance(activity, EventActivityOverTime):
            raise TypeError(
                f"{_ERROR_PREFIX}: activity must be an EventActivityOverTime "
                f"object, got {type(activity).__name__}"
            )
        if config is None:
            config = ActivityOverTimeConfig()
        if not isinstance(config, ActivityOverTimeConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an ActivityOverTimeConfig "
                f"object, got {type(config).__name__}"
            )

        self._activity = activity
        self._config   = config

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """
        Save the activity over time plot to a file (.png, .jpg, .jpeg).

        Parameters
        ----------
        path : str
            Output file path.
        """
        from .activity_over_time_plotter_utils import (
            render_line_panel, render_arrow_panel,
        )

        self._validate_path(path)

        cfg      = self._config
        canvas   = cfg.canvas
        ts       = self._activity.data
        max_days = self._activity.max_days

        if cfg.time.mpl_style is not None:
            try:
                plt.style.use(cfg.time.mpl_style)
            except Exception:
                pass

        show_flow = cfg.flow_style.enabled

        if show_flow:
            fig, axes = plt.subplots(
                2, 1,
                figsize     = canvas.figsize,
                sharex      = True,
                gridspec_kw = {
                    "height_ratios": [
                        cfg.layout.top_height_ratio,
                        cfg.layout.bottom_height_ratio,
                    ]
                },
            )
            ax_line  = axes[0]
            ax_arrow = axes[1]
        else:
            fig, ax_line = plt.subplots(figsize=canvas.figsize)
            ax_arrow = None

        render_line_panel(
            ax           = ax_line,
            ts           = ts,
            cfg          = cfg,
            max_days     = max_days,
            mode         = self._activity.mode,
            cohort_start = self._activity.cohort_start,
        )

        if show_flow and ax_arrow is not None:
            render_arrow_panel(
                ax           = ax_arrow,
                ts           = ts,
                cfg          = cfg,
                max_days     = max_days,
                mode         = self._activity.mode,
                cohort_start = self._activity.cohort_start,
            )

        fig.tight_layout()
        fig.savefig(path, dpi=canvas.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _validate_path(self, path: str) -> None:
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
                f"Use .png, .jpg, or .jpeg"
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"ActivityOverTimePlotter(\n"
            f"  mode         : '{self._activity.mode}'\n"
            f"  cohort_start : {self._activity.cohort_start}\n"
            f"  timepoints   : {len(self._activity):,}\n"
            f"  n_entities   : {self._activity.n_entities:,}\n"
            f"  flow_style   : enabled={self._config.flow_style.enabled} "
            f"mode={self._config.flow_style.mode!r}\n"
            f")"
        )
