"""
episode_duration_histogram_plotter.py
EpisodeDurationHistogramPlotter — histogram and KDE plots of episode
durations from an EpisodeDurationResult.

No stratification — use EpisodeDurationViolinPlotter for group comparisons.

Plot methods
------------
plot_histogram(path) — binned histogram of duration_days
plot_kde(path)       — KDE density curve of duration_days
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from eventus.intermediates.episode_duration_result import EpisodeDurationResult
from eventus.visualizers.configs.episode_duration_plot_config import EpisodeDurationPlotConfig
from eventus.visualizers.plot_utils import validate_path, save_figure
from eventus.visualizers.histogram_utils import compute_bins, draw_percentile_lines

_ERROR = "[EpisodeDurationHistogramPlotter] Error"


class EpisodeDurationHistogramPlotter:
    """
    Histogram and KDE density curve plots of episode durations.

    No stratification — the violin plotter handles group comparisons.
    This plotter focuses on the distribution shape of the full cohort.

    Parameters
    ----------
    duration_result : EpisodeDurationResult
        Produced by EpisodeDurationAnalyzer.calc().
    config : EpisodeDurationPlotConfig | None
        Plot configuration. Uses EpisodeDurationPlotConfig() defaults
        if not provided.

    Examples
    --------
    >>> duration_result  = EpisodeDurationAnalyzer(episodes).calc()
    >>> config  = EpisodeDurationPlotConfig.build_from_yaml("duration.yaml")
    >>> plotter = EpisodeDurationHistogramPlotter(result, config)
    >>> plotter.plot_histogram("duration_histogram.png")
    >>> plotter.plot_kde("duration_kde.png")
    """

    def __init__(
        self,
        duration_result: EpisodeDurationResult,
        config: EpisodeDurationPlotConfig | None = None,
    ) -> None:
        if not isinstance(duration_result, EpisodeDurationResult):
            raise TypeError(
                f"{_ERROR}: result must be an EpisodeDurationResult, "
                f"got {type(duration_result).__name__}"
            )
        if config is None:
            config = EpisodeDurationPlotConfig()
        if not isinstance(config, EpisodeDurationPlotConfig):
            raise TypeError(
                f"{_ERROR}: config must be an EpisodeDurationPlotConfig, "
                f"got {type(config).__name__}"
            )

        self._duration_result = duration_result
        self._config = config

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_histogram(self, path: str) -> None:
        """
        Plot a binned histogram of duration_days.

        Bin strategy, color, percentile lines, and labels are all
        controlled by config.histogram (HistogramPlotConfig).

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        validate_path(path, _ERROR)

        cfg       = self._config
        hist_cfg  = cfg.histogram
        canvas    = cfg.canvas
        durations = self._durations()

        fig, ax = plt.subplots(figsize=canvas.figsize)

        # Draw histogram
        bins  = compute_bins(durations, hist_cfg.bins)
        style = hist_cfg.style
        ax.hist(
            durations.to_numpy(),
            bins      = bins,
            color     = style.color,
            edgecolor = style.edgecolor,
            alpha     = style.alpha,
        )

        if style.show_grid:
            ax.yaxis.grid(True, linestyle="--", alpha=0.4)
            ax.set_axisbelow(True)

        # Percentile lines
        draw_percentile_lines(ax, durations, hist_cfg.percentile_lines)

        # Labels
        self._apply_labels(ax, hist_cfg.labels, canvas.font_size, "histogram")

        # n label
        ax.text(
            0.98, 0.97,
            f"n={len(durations):,} episodes",
            transform = ax.transAxes,
            ha        = "right",
            va        = "top",
            fontsize  = canvas.font_size - 1,
            color     = "#555555",
        )

        fig.tight_layout()
        save_figure(fig, path, canvas.dpi)

    def plot_kde(self, path: str) -> None:
        """
        Plot a KDE density curve of duration_days.

        Bandwidth, color, fill, linewidth, and percentile lines are all
        controlled by config.kde (KDEPlotConfig).

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        validate_path(path, _ERROR)

        cfg       = self._config
        kde_cfg   = cfg.kde
        canvas    = cfg.canvas
        style     = kde_cfg.style
        durations = self._durations()

        if len(durations) < 2:
            raise ValueError(
                f"{_ERROR}: plot_kde() requires at least 2 finite duration "
                f"values, got {len(durations)}."
            )

        fig, ax = plt.subplots(figsize=canvas.figsize)

        # Compute KDE
        arr = durations.to_numpy(dtype=np.float64)
        kde = gaussian_kde(arr, bw_method=style.bandwidth)

        x_min  = max(0.0, float(arr.min()))
        x_max  = float(arr.max())
        x_grid = np.linspace(x_min, x_max, 500)
        y_grid = kde(x_grid)

        # Draw line
        ax.plot(
            x_grid, y_grid,
            color     = style.color,
            linewidth = style.linewidth,
            alpha     = style.alpha,
            zorder    = 3,
        )

        # Fill under curve
        if style.fill_alpha > 0:
            ax.fill_between(
                x_grid, y_grid,
                alpha  = style.fill_alpha,
                color  = style.color,
                zorder = 2,
            )

        if style.show_grid:
            ax.yaxis.grid(True, linestyle="--", alpha=0.4)
            ax.set_axisbelow(True)

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(bottom=0)

        # Percentile lines
        draw_percentile_lines(ax, durations, kde_cfg.percentiles)

        # Labels
        self._apply_labels(ax, kde_cfg.labels, canvas.font_size, "kde")

        # n label
        ax.text(
            0.98, 0.97,
            f"n={len(durations):,} episodes",
            transform = ax.transAxes,
            ha        = "right",
            va        = "top",
            fontsize  = canvas.font_size - 1,
            color     = "#555555",
        )

        fig.tight_layout()
        save_figure(fig, path, canvas.dpi)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _durations(self) -> pd.Series:
        """Return duration_days as a clean Series with NaNs dropped."""
        return (
            self._duration_result.data["duration_days"]
            .dropna()
            .reset_index(drop=True)
        )

    def _apply_labels(
        self,
        ax,
        labels,
        font_size: int,
        plot_type: str,
    ) -> None:
        """Apply title, xlabel, ylabel from config labels."""
        identity = self._duration_result.identity

        # Title — config first, then auto
        title = labels.title
        if title is None:
            suffix = "Distribution" if plot_type == "histogram" else "Density"
            title  = (
                f"Duration {suffix} — {identity}"
                if identity
                else f"Episode Duration {suffix}"
            )
        ax.set_title(title, fontsize=font_size + 1)

        xlabel = labels.xlabel or (
            f"Duration ({labels.units})" if labels.units else "Duration (days)"
        )
        ylabel = labels.ylabel or (
            "Entities" if plot_type == "histogram" else "Density"
        )

        ax.set_xlabel(xlabel, fontsize=font_size)
        ax.set_ylabel(ylabel, fontsize=font_size)
        ax.tick_params(labelsize=font_size - 1)

        if labels.subtitle:
            ax.text(
                0.98, 0.89,
                labels.subtitle,
                transform = ax.transAxes,
                ha        = "right",
                va        = "top",
                fontsize  = font_size - 1,
                color     = "#555555",
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EpisodeDurationHistogramPlotter(\n"
            f"  identity   : {self._duration_result.identity!r}\n"
            f"  n_episodes   : {self._duration_result.n_episodes:,}\n"
            f"  n_entities : {self._duration_result.n_entities:,}\n"
            f")"
        )
