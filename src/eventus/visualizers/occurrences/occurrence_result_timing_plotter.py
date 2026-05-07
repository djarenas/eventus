"""
occurrence_result_timing_plotter.py
OccurrenceResultTimingPlotter — plots for OccurrenceResultTiming.

Plot methods
------------
plot_histogram(path)            — faceted nth-occurrence timing histograms
plot_survival(path, survival)   — KM survival curve
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.occurrence_result_timing import OccurrenceResultTiming
from eventus.intermediates.survival_result          import SurvivalResult
from .occurrence_result_plotter_config import OccurrenceResultTimingConfig
from . import occurrence_result_plotter_utils        as shared_utils
from . import occurrence_result_timing_plotter_utils as timing_utils

_ERROR = "[OccurrenceResultTimingPlotter] Error"


class OccurrenceResultTimingPlotter:
    """
    I plot occurrence timing statistics from an OccurrenceResultTiming.

    Parameters
    ----------
    timing : OccurrenceResultTiming
    config : OccurrenceResultTimingConfig | None
        Plot configuration. Uses build_with_defaults() if not provided.
    """

    _timing: OccurrenceResultTiming
    _config: OccurrenceResultTimingConfig

    def __init__(
        self,
        timing: OccurrenceResultTiming,
        config: OccurrenceResultTimingConfig | None = None,
    ) -> None:
        if not isinstance(timing, OccurrenceResultTiming):
            raise TypeError(
                f"{_ERROR} timing must be an OccurrenceResultTiming, "
                f"got {type(timing).__name__}"
            )
        if config is None:
            config = OccurrenceResultTimingConfig.build_with_defaults()
        if not isinstance(config, OccurrenceResultTimingConfig):
            raise TypeError(
                f"{_ERROR} config must be an OccurrenceResultTimingConfig, "
                f"got {type(config).__name__}"
            )
        self._timing = timing
        self._config = config

    # ------------------------------------------------------------------ #
    # Plot methods
    # ------------------------------------------------------------------ #

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

        cfg    = self._config
        data   = self._timing.data
        max_n  = self._timing.max_n

        # Collect all nth series for shared x-limit computation
        nth_series = {
            nth: data[f"time_to_{nth}"].astype(float)
            for nth in range(1, max_n + 1)
        }

        # Shared x limits — computed across all nths
        x_min, x_max = shared_utils.resolve_x_limits(
            series_list = list(nth_series.values()),
            cfg         = cfg.histogram,
        )

        fig, axes = timing_utils.build_faceted_figure(
            max_n        = max_n,
            facet_height = cfg.facet.facet_height,
            facet_width  = cfg.facet.facet_width,
        )

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = axes,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = f"Time to nth occurrence — {self._timing.identity}",
        )

        for nth, ax in zip(range(1, max_n + 1), axes):
            series      = nth_series[nth]
            n_eligible  = int(series.notna().sum())
            hist_cfg    = cfg.resolve_histogram_for_nth(nth)

            timing_utils.draw_nth_facet(
                ax                     = ax,
                series                 = series,
                nth                    = nth,
                x_min                  = x_min,
                x_max                  = x_max,
                histogram_cfg          = hist_cfg,
                font_size              = cfg.general.font_size,
                n_eligible             = n_eligible,
                n_total                = self._timing.n_entities,
                show_denominator_label = True,
            )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

    def plot_survival(
        self,
        path:     str,
        survival: SurvivalResult,
    ) -> None:
        """
        Plot a Kaplan-Meier survival curve from a SurvivalResult.

        The curve shows the probability of NOT yet having a first
        occurrence by day t. Entities with no occurrence are correctly
        treated as right-censored at their obs_duration.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        survival : SurvivalResult
            Produced by CohortTimelineOccurrenceAnalyzer.compute_survival().
        """
        shared_utils.validate_path(path, _ERROR)

        if not isinstance(survival, SurvivalResult):
            raise TypeError(
                f"{_ERROR} survival must be a SurvivalResult, "
                f"got {type(survival).__name__}"
            )

        cfg = self._config
        fig, ax = plt.subplots(
            figsize=cfg.general.figsize or [10, 6]
        )

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = (
                f"Time to first {survival.label} — KM survival curve\n"
                f"n={survival.n_total:,}  |  "
                f"events={survival.n_events_total:,} ({survival.event_rate_pct}%)  |  "
                f"censored={survival.n_censored_total:,}"
            ),
        )

        if survival.data.empty:
            ax.text(
                0.5, 0.5, "No events observed — survival curve unavailable",
                transform = ax.transAxes,
                ha        = "center",
                va        = "center",
                fontsize  = cfg.general.font_size,
                color     = "#AAAAAA",
            )
        else:
            timing_utils.draw_survival_curve(
                ax            = ax,
                survival_data = survival.data,
                curve_cfg     = cfg.survival,
                font_size     = cfg.general.font_size,
                label         = survival.label,
            )

            median = survival.median_survival
            if median is not None:
                ax.axvline(
                    x         = median,
                    color     = cfg.survival.color,
                    linestyle = "--",
                    linewidth = 1.0,
                    alpha     = 0.5,
                )
                ax.text(
                    median + 1,
                    0.52,
                    f"median={median:.0f}d",
                    fontsize = cfg.general.font_size - 1,
                    color    = cfg.survival.color,
                )

            if cfg.survival.show_ci:
                ax.legend(fontsize=cfg.general.font_size - 1)

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultTimingPlotter(\n"
            f"  identity : '{self._timing.identity}'\n"
            f"  entities : {self._timing.n_entities:,}\n"
            f"  max_n    : {self._timing.max_n}\n"
            f")"
        )
