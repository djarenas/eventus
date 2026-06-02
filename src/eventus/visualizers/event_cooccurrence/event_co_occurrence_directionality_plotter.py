"""
event_co_occurrence_directionality_plotter.py
EventCoOccurrenceDirectionalityPlotter — KDE plot of observed vs
permutation null signed gap distributions.

Single-panel figure centered at zero.
Positive x = A tends to precede B.
Negative x = B tends to precede A.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_test import (
    EventCoOccurrenceDirectionalityTest,
)

_ERROR = "[EventCoOccurrenceDirectionalityPlotter] Error"


class EventCoOccurrenceDirectionalityPlotter:
    """
    Single-panel KDE plot of observed vs permutation null signed gaps.

    Parameters
    ----------
    dir_test : EventCoOccurrenceDirectionalityTest
    config   : EventCoOccurrenceDirectionalityPlotConfig (optional)
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _test:   EventCoOccurrenceDirectionalityTest        # validated test result input
    _config: "EventCoOccurrenceDirectionalityPlotConfig"  # plot configuration

    def __init__(self, dir_test, config=None) -> None:
        if not isinstance(dir_test, EventCoOccurrenceDirectionalityTest):
            raise TypeError(
                f"{_ERROR}: dir_test must be an "
                f"EventCoOccurrenceDirectionalityTest."
            )
        from eventus.visualizers.configs.event_co_occurrence_directionality_plot_config import (
            EventCoOccurrenceDirectionalityPlotConfig,
        )
        if config is None:
            config = EventCoOccurrenceDirectionalityPlotConfig.defaults()
        self._test   = dir_test
        self._config = config

    def plot(self, path: str) -> None:
        cfg = self._config
        t   = self._test

        obs_clean  = t.observed_signed_gaps[~np.isnan(t.observed_signed_gaps)]
        null_clean = t.null_signed_gaps[~np.isnan(t.null_signed_gaps)]

        fig, ax = plt.subplots(figsize=cfg.figsize, dpi=cfg.dpi)

        fig.suptitle(
            f"Directionality: {t.identity_a} ↔ {t.identity_b}\n"
            f"n_co_occurring={t.n_co_occurring:,}  "
            f"fraction_a_first={round(t.fraction_a_first*100,1)}%  "
            f"Wilcoxon p={t._fmt_p(t.wilcoxon_p)}",
            fontsize=cfg.font_size + 1,
        )

        if len(obs_clean) >= 2 and len(null_clean) >= 2:
            x_min = min(obs_clean.min(), null_clean.min()) * 1.1
            x_max = max(obs_clean.max(), null_clean.max()) * 1.1
            x     = np.linspace(x_min, x_max, 500)

            # Null KDE
            kde_null = gaussian_kde(null_clean, bw_method=cfg.bandwidth)
            y_null   = kde_null(x)
            ax.fill_between(x, y_null, alpha=cfg.alpha_null,
                            color=cfg.color_null, label="Permutation null")
            ax.plot(x, y_null, color=cfg.color_null, linewidth=1.5)

            # Observed KDE
            kde_obs = gaussian_kde(obs_clean, bw_method=cfg.bandwidth)
            y_obs   = kde_obs(x)
            ax.fill_between(x, y_obs, alpha=cfg.alpha_observed,
                            color=cfg.color_observed, label="Observed")
            ax.plot(x, y_obs, color=cfg.color_observed, linewidth=2)

            # Zero line
            if cfg.show_zero_line:
                ax.axvline(0, color="black", linestyle="-",
                           linewidth=1.0, alpha=0.4, label="Zero (no direction)")

            # Mean lines
            if cfg.show_means:
                obs_mean  = float(np.mean(obs_clean))
                null_mean = float(np.mean(null_clean))
                ax.axvline(obs_mean,  color=cfg.color_observed,
                           linestyle="--", linewidth=1.5, alpha=0.9,
                           label=f"Observed mean: {obs_mean:.0f}d")
                ax.axvline(null_mean, color=cfg.color_null,
                           linestyle="--", linewidth=1.5, alpha=0.9,
                           label=f"Null mean: {null_mean:.0f}d")

        ax.set_xlabel(
            f"Mean signed gap (days)\n"
            f"← {t.identity_b} first   |   {t.identity_a} first →",
            fontsize=cfg.font_size - 1
        )
        ax.set_ylabel("Density", fontsize=cfg.font_size - 1)
        ax.legend(fontsize=cfg.font_size - 2, loc="upper right")
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=cfg.font_size - 2)
        ax.grid(True, alpha=0.3, linewidth=0.5)

        plt.tight_layout()
        plt.savefig(path, bbox_inches="tight")
        plt.close()
