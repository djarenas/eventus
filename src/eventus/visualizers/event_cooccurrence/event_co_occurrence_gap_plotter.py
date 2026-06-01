"""
event_co_occurrence_gap_plotter.py
EventCoOccurrenceGapPlotter — KDE plot of observed vs permutation null
gap distributions from an EventCoOccurrenceGapTest.

Two-panel figure:
  Top panel    : A → nearest B
  Bottom panel : B → nearest A

Each panel shows:
  - KDE of observed per-entity median gaps (solid)
  - KDE of permutation null gaps (filled, semi-transparent)
  - Vertical lines at observed and null medians (if show_medians=True)
  - KS statistic and p-value annotation (if show_ks=True)
"""
from __future__ import annotations

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import gaussian_kde

from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_test import (
    EventCoOccurrenceGapTest,
)

_ERROR = "[EventCoOccurrenceGapPlotter] Error"


class EventCoOccurrenceGapPlotter:
    """
    KDE plot of observed vs permutation null gap distributions.

    Parameters
    ----------
    gap_test : EventCoOccurrenceGapTest
    config   : EventCoOccurrenceGapPlotConfig (optional — uses defaults)

    Examples
    --------
    >>> plotter = EventCoOccurrenceGapPlotter(gap_test)
    >>> plotter.plot("output/gap_distributions.png")

    >>> # Custom config
    >>> config  = EventCoOccurrenceGapPlotConfig(bandwidth="silverman")
    >>> plotter = EventCoOccurrenceGapPlotter(gap_test, config)
    >>> plotter.plot("output/gap_distributions.png")
    """

    def __init__(self, gap_test, config=None) -> None:
        if not isinstance(gap_test, EventCoOccurrenceGapTest):
            raise TypeError(
                f"{_ERROR}: gap_test must be an EventCoOccurrenceGapTest, "
                f"got {type(gap_test).__name__}"
            )
        from eventus.visualizers.configs.event_co_occurrence_gap_plot_config import (
            EventCoOccurrenceGapPlotConfig,
        )
        if config is None:
            config = EventCoOccurrenceGapPlotConfig.defaults()
        if not isinstance(config, EventCoOccurrenceGapPlotConfig):
            raise TypeError(
                f"{_ERROR}: config must be an EventCoOccurrenceGapPlotConfig."
            )
        self._test   = gap_test
        self._config = config

    def plot(self, path: str) -> None:
        """
        Save a two-panel KDE figure to path.

        Parameters
        ----------
        path : str — output file path (e.g. 'output/gap_distributions.png')
        """
        cfg = self._config
        t   = self._test

        fig, axes = plt.subplots(
            2, 1,
            figsize    = cfg.figsize,
            dpi        = cfg.dpi,
            sharex     = False,
        )
        fig.suptitle(
            f"Gap distributions: {t.identity_a} ↔ {t.identity_b}\n"
            f"n_co_occurring={t.n_co_occurring:,}  "
            f"null: {t.null_method} (n_permutations={t.n_permutations:,})",
            fontsize = cfg.font_size + 1,
            y        = 1.01,
        )

        panels = [
            (
                axes[0],
                t.observed_gaps_a_to_b,
                t.null_gaps_a_to_b,
                f"{t.identity_a} → nearest {t.identity_b}",
            ),
            (
                axes[1],
                t.observed_gaps_b_to_a,
                t.null_gaps_b_to_a,
                f"{t.identity_b} → nearest {t.identity_a}",
            ),
        ]

        for ax, obs, null, title in panels:
            self._draw_panel(ax, obs, null, title, cfg)

        plt.tight_layout()
        plt.savefig(path, bbox_inches="tight")
        plt.close()

    def _draw_panel(
        self,
        ax,
        obs:   np.ndarray,
        null:  np.ndarray,
        title: str,
        cfg,
    ) -> None:
        obs_clean  = obs[~np.isnan(obs)]
        null_clean = null[~np.isnan(null)]

        if len(obs_clean) < 2 or len(null_clean) < 2:
            ax.text(0.5, 0.5, "Insufficient data", transform=ax.transAxes,
                    ha="center", va="center")
            return

        # Shared x range
        x_min = 0
        x_max = max(obs_clean.max(), null_clean.max()) * 1.05
        x     = np.linspace(x_min, x_max, 500)

        bw = cfg.bandwidth

        # KDE — null (draw first, behind)
        kde_null = gaussian_kde(null_clean, bw_method=bw)
        y_null   = kde_null(x)
        ax.fill_between(x, y_null, alpha=cfg.alpha_null,
                        color=cfg.color_null, label="Permutation null")
        ax.plot(x, y_null, color=cfg.color_null, linewidth=1.5)

        # KDE — observed (draw on top)
        kde_obs = gaussian_kde(obs_clean, bw_method=bw)
        y_obs   = kde_obs(x)
        ax.fill_between(x, y_obs, alpha=cfg.alpha_observed,
                        color=cfg.color_observed, label="Observed")
        ax.plot(x, y_obs, color=cfg.color_observed, linewidth=2)

        # Median lines
        if cfg.show_medians:
            obs_med  = float(np.median(obs_clean))
            null_med = float(np.median(null_clean))
            ax.axvline(obs_med,  color=cfg.color_observed, linestyle="--",
                       linewidth=1.5, alpha=0.9,
                       label=f"Observed median: {obs_med:.0f}d")
            ax.axvline(null_med, color=cfg.color_null,     linestyle="--",
                       linewidth=1.5, alpha=0.9,
                       label=f"Null median: {null_med:.0f}d")

        # KS annotation


        ax.set_title(title, fontsize=cfg.font_size, pad=8)
        ax.set_xlabel("Median gap to nearest event (days)", fontsize=cfg.font_size - 1)
        ax.set_ylabel("Density", fontsize=cfg.font_size - 1)
        ax.legend(fontsize=cfg.font_size - 2, loc="upper right")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=cfg.font_size - 2)
        ax.grid(True, alpha=0.3, linewidth=0.5)
