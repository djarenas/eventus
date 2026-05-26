"""
event_result_timing_plotter.py
EventResultTimingPlotter — plots for EventResultTiming.

Plot methods
------------
plot_histogram(path) — faceted nth-event timing histograms, one per nth,
                       all sharing the same x-axis scale
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.event_result_timing import EventResultTiming
from eventus.visualizers.configs.event_result_timing_config import EventResultTimingConfig
from eventus.visualizers.events import event_result_plotter_utils        as shared_utils
from eventus.visualizers.events import event_result_timing_plotter_utils as timing_utils

_ERROR = "[EventResultTimingPlotter]"


class EventResultTimingPlotter:
    """
    I plot event timing statistics from an EventResultTiming.

    Parameters
    ----------
    timing : EventResultTiming
    config : EventResultTimingConfig | None
        Plot configuration. Defaults to EventResultTimingConfig() if not provided.
    """

    _timing: EventResultTiming
    _config: EventResultTimingConfig

    def __init__(
        self,
        timing: EventResultTiming,
        config: EventResultTimingConfig | None = None,
    ) -> None:
        if not isinstance(timing, EventResultTiming):
            raise TypeError(
                f"{_ERROR} timing must be an EventResultTiming, "
                f"got {type(timing).__name__}"
            )
        if config is None:
            config = EventResultTimingConfig()
        if not isinstance(config, EventResultTimingConfig):
            raise TypeError(
                f"{_ERROR} config must be an EventResultTimingConfig, "
                f"got {type(config).__name__}"
            )
        self._timing = timing
        self._config = config

    # ── Plot methods ──────────────────────────────────────────────────────────

    def plot_histogram(self, path: str) -> None:
        """
        Plot faceted histograms of time_to_nth for each nth up to max_n.
        All facets share the same x-axis scale.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg   = self._config
        data  = self._timing.data
        max_n = self._timing.max_n

        # Collect all nth series
        nth_series = {
            nth: data[f"time_to_{nth}"].astype(float)
            for nth in range(1, max_n + 1)
        }

        # Shared x limits — computed from the base histogram bins across all nths
        x_min, x_max = shared_utils.resolve_x_limits(
            series_list = list(nth_series.values()),
            bins_cfg    = cfg.histogram.bins,
        )

        fig, axes = timing_utils.build_faceted_figure(
            max_n        = max_n,
            facet_height = cfg.facet.facet_height,
            facet_width  = cfg.facet.facet_width,
        )

        shared_utils.apply_style(
            fig        = fig,
            axes       = axes,
            canvas     = cfg.canvas,
            labels     = cfg.histogram.labels,
            auto_title = f"Time to nth event — {self._timing.identity}",
        )

        for nth, ax in zip(range(1, max_n + 1), axes):
            # Resolution logic lives here in the plotter, not in the config
            hist_cfg   = cfg.histogram_per_n.get(nth, cfg.histogram)
            series     = nth_series[nth]
            n_eligible = int(series.notna().sum())

            timing_utils.draw_nth_facet(
                ax                     = ax,
                series                 = series,
                nth                    = nth,
                x_min                  = x_min,
                x_max                  = x_max,
                histogram_cfg          = hist_cfg,
                font_size              = cfg.canvas.font_size,
                n_eligible             = n_eligible,
                n_total                = self._timing.n_entities,
                show_denominator_label = True,
            )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"EventResultTimingPlotter(\n"
            f"  identity : '{self._timing.identity}'\n"
            f"  entities : {self._timing.n_entities:,}\n"
            f"  max_n    : {self._timing.max_n}\n"
            f")"
        )
