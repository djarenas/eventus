"""
activity_over_time_plotter.py
ActivityOverTimePlotter — visualize cohort activity over time.

Two panels:
  Top    — line chart of fraction of entities active at each timepoint
  Bottom — diverging bar chart of entities entering and exiting

Takes a CohortTimeline object and an event identity.
Delegates timeseries computation to CohortTimelineEventAnalyzer.activity_over_time().
"""
from __future__ import annotations
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .activity_over_time_config import ActivityOverTimeConfig
from eventus.cohort_timeline.cohort_timeline import CohortTimeline
from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer

_ERROR_PREFIX = "[ActivityOverTimePlotter] Error"


class ActivityOverTimePlotter:
    """
    I can visualize event-activity of a cohort over an observation period.

    Takes a CohortTimeline and an event identity. The CohortTimeline must
    have an observation period and the named event identity.

    Top panel shows what fraction of the cohort is active at each timepoint.
    Bottom panel shows a diverging bar chart of entries and exits — revealing
    the flow behind the activity curve. A flat activity line with large bars
    in both directions tells a different story than a flat line with no movement.

    Parameters
    ----------
    cohort_timeline : CohortTimeline
    identity : str
        The event identity to visualize. Must be present in
        cohort_timeline.event_identities.
    config : ActivityOverTimeConfig | None
        Plot configuration. Uses ActivityOverTimeConfig.build_with_defaults()
        if not provided.
    granularity : str
        Time resolution — "day", "week", or "month". Default "week".

    Examples
    --------
    >>> plotter = ActivityOverTimePlotter(ct, identity="treatment")
    >>> plotter.plot("activity.png")

    >>> config  = ActivityOverTimeConfig.build_from_yaml("config.yaml")
    >>> plotter = ActivityOverTimePlotter(ct, "treatment", config, granularity="month")
    >>> plotter.plot("activity.png")
    """

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        identity:        str,
        config           = None,
        granularity: str = "week",
    ) -> None:

        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR_PREFIX}: cohort_timeline must be a CohortTimeline "
                f"object, got {type(cohort_timeline).__name__}"
            )

        if not isinstance(identity, str) or not identity.strip():
            raise TypeError(
                f"{_ERROR_PREFIX}: identity must be a non-empty string, "
                f"got {identity!r}"
            )

        if not cohort_timeline.has_obs_period:
            raise ValueError(
                f"{_ERROR_PREFIX}: cohort_timeline has no observation period. "
                f"ActivityOverTimePlotter requires obs_start and obs_end columns."
            )

        if identity not in cohort_timeline.event_identities:
            raise ValueError(
                f"{_ERROR_PREFIX}: identity '{identity}' not found in "
                f"cohort_timeline. "
                f"Available event identities: {cohort_timeline.event_identities}"
            )

        if granularity not in {"day", "week", "month"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: granularity must be 'day', 'week', or 'month', "
                f"got {granularity!r}"
            )

        if config is None:
            config = ActivityOverTimeConfig.build_with_defaults()
        if not isinstance(config, ActivityOverTimeConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an ActivityOverTimeConfig "
                f"object, got {type(config).__name__}"
            )

        self._cohort_timeline = cohort_timeline
        self._identity        = identity
        self._config          = config
        self._granularity     = granularity

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

        cfg  = self._config
        gcfg = cfg.general

        # Compute timeseries via CohortTimelineEventAnalyzer.activity_over_time(),
        # which owns all column logic for this identity.
        # Returns a DataFrame with 'day', 'pct_active', 'n_entered', 'n_exited'.
        analyzer = CohortTimelineEventAnalyzer(self._cohort_timeline, self._identity)
        ts       = analyzer.activity_over_time(granularity=self._granularity)
        max_days = int(ts["day"].max())

        try:
            plt.style.use(gcfg.style)
        except Exception:
            pass

        show_arrows = cfg.arrows.show

        if show_arrows:
            fig, axes = plt.subplots(
                2, 1,
                figsize     = gcfg.figsize,
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
            fig, ax_line = plt.subplots(figsize=gcfg.figsize)
            ax_arrow = None

        render_line_panel(ax_line, ts, cfg, max_days)

        if show_arrows and ax_arrow is not None:
            render_arrow_panel(ax_arrow, ts, cfg, max_days)

        fig.tight_layout()
        fig.savefig(path, dpi=gcfg.dpi, bbox_inches="tight")
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
            f"  identity    : '{self._identity}'\n"
            f"  entities    : {len(self._cohort_timeline):,}\n"
            f"  granularity : '{self._granularity}'\n"
            f"  x_unit      : '{self._config.general.x_unit}'\n"
            f"  arrows      : show={self._config.arrows.show} "
            f"style={self._config.arrows.style!r}\n"
            f")"
        )
