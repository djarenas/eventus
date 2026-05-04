"""
activity_over_time_plotter.py
ActivityOverTimePlotter — visualize cohort activity over time.

Two panels:
  Top    — line chart of fraction of entities active at each timepoint
  Bottom — diverging bar chart of entities entering and exiting

Takes a PipeDelimitedFormatEvents object directly.
Calls activity_over_time() internally.
"""
from __future__ import annotations
import pathlib
import warnings
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Add the inner package folder directly to sys.path  
import sys
sys.path.append(r"C:/Users/DanielArenas/Desktop/Github_Local/Python_Events_Classes")  


_ERROR_PREFIX = "[ActivityOverTimePlotter] Error"


class ActivityOverTimePlotter:
    """
    Visualize cohort activity over time from a PipeDelimitedFormatEvents.

    Top panel shows what fraction of the cohort is active at each timepoint.
    Bottom panel shows a diverging bar chart of entries and exits — revealing
    the flow behind the activity curve. A flat activity line with large bars
    in both directions tells a different story than a flat line with no movement.

    Parameters
    ----------
    intermediate : PipeDelimitedFormatEvents
        Must have been produced by EventsWithinObsPeriodsAnalyzer.
    config : ActivityOverTimeConfig | None
        Plot configuration. Uses ActivityOverTimeConfig.build_with_defaults()
        if not provided.
    granularity : int
        Day-bucket size for the timeseries. Default 7 (weekly).

    Examples
    --------
    >>> plotter = ActivityOverTimePlotter(events_result)
    >>> plotter.plot("activity.png")

    >>> config  = ActivityOverTimeConfig.build_from_yaml("config.yaml")
    >>> plotter = ActivityOverTimePlotter(events_result, config, granularity=30)
    >>> plotter.plot("activity.png")
    """

    def __init__(
        self,
        intermediate,
        config       = None,
        granularity: str = "week",  # "day", "week", or "month"
    ) -> None:
        from eventus.pipe_delimited_format.pipe_delimited_format_events import PipeDelimitedFormatEvents
        from .activity_over_time_config import ActivityOverTimeConfig

        if not isinstance(intermediate, PipeDelimitedFormatEvents):
            raise TypeError(
                f"{_ERROR_PREFIX}: intermediate must be a "
                f"PipeDelimitedFormatEvents object, "
                f"got {type(intermediate).__name__}"
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

        self._intermediate  = intermediate
        self._config        = config
        self._granularity   = granularity

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

        # ── Compute timeseries ────────────────────────────────────────
        ts = self._intermediate.activity_over_time(
            granularity=self._granularity
        )
        max_days = int(ts["day"].max())

        # ── Figure layout ─────────────────────────────────────────────
        try:
            plt.style.use(gcfg.style)
        except Exception:
            pass

        show_arrows = cfg.arrows.show

        if show_arrows:
            fig, axes = plt.subplots(
                2, 1,
                figsize      = gcfg.figsize,
                sharex       = True,
                gridspec_kw  = {
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

        # ── Render panels ─────────────────────────────────────────────
        render_line_panel(ax_line, ts, cfg, max_days)

        if show_arrows and ax_arrow is not None:
            render_arrow_panel(ax_arrow, ts, cfg, max_days)

        fig.tight_layout()
        fig.savefig(path, dpi=gcfg.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
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
            f"ActivityOverTimePlotter(\n"
            f"  entities    : {len(self._intermediate):,}\n"
            f"  granularity : '{self._granularity}'\n"
            f"  x_unit      : '{self._config.general.x_unit}'\n"
            f"  arrows      : show={self._config.arrows.show} "
            f"style={self._config.arrows.style!r}\n"
            f")"
        )
