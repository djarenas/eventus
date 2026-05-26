"""
episode_coverage_violin_plotter.py
EpisodeCoverageViolinPlotter — violin plots from a CohortTimeline with
episode coverage analysis columns.

Two plot methods:
  plot_total()              — eps_comp_{identity}_active_days vs inactive_days
  plot_inactive_breakdown() — inactive metrics, filtered to > 0

Drawing is delegated entirely to ArraysViolinPlotter.
This class is responsible for:
  - validating the CohortTimeline has the required columns
  - building the short-keyed arrays from eps_comp_{identity}_* columns
  - applying unit conversion
  - passing clean arrays + config to ArraysViolinPlotter
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter
from eventus.visualizers.plot_utils import validate_path, save_figure

_ERROR_PREFIX = "[EpisodeCoverageViolinPlotter] Error"

# Short metric names used in plot_total
_TOTAL_METRICS = {"active_days", "inactive_days"}

# Short metric names used in plot_inactive_breakdown, in fixed display order
_BREAKDOWN_METRICS = [
    "inactive_days_before_first_episode",
    "inactive_days_after_last_episode",
    "inactive_days_middle",
]


def _required_cols(identity: str) -> set[str]:
    """Return all required eps_comp_{identity}_* column names."""
    p = f"eps_comp_{identity}_"
    return {
        "obs_duration_days",
        f"{p}active_days",
        f"{p}inactive_days",
        f"{p}inactive_days_before_first_episode",
        f"{p}inactive_days_after_last_episode",
        f"{p}inactive_days_middle",
        f"{p}first_start",
        f"{p}last_end",
    }


class EpisodeCoverageViolinPlotter:
    """
    Violin plots from a CohortTimeline with episode coverage analysis columns.

    The CohortTimeline must already have analysis columns for the given
    identity — produced by CohortTimelineEpisodeAnalyzer.compute_coverage().

    Drawing is handled by ArraysViolinPlotter. Pass an ArraysViolinConfig
    to control colors, labels, style, and percentile lines. If config has
    no categories defined, colors are auto-assigned from the default palette.

    Parameters
    ----------
    cohort_timeline : CohortTimeline
        Must have comp_{identity}_* analysis columns present.
        Call CohortTimelineEpisodeAnalyzer(ct, identity).compute_coverage() first.
    identity : str
        Episode identity whose columns to plot.
    config : ArraysViolinConfig | None
        Plot configuration. Uses ArraysViolinConfig() defaults if not provided.

    Examples
    --------
    >>> ct      = CohortTimelineEpisodeAnalyzer(ct, "inpatient").compute_coverage()
    >>> config  = ArraysViolinConfig.build_from_yaml("coverage_violin.yaml")
    >>> plotter = EpisodeCoverageViolinPlotter(ct, identity="inpatient", config=config)
    >>> plotter.plot_total("total.png")
    >>> plotter.plot_inactive_breakdown("breakdown.png")
    """

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        identity:        str,
        config:          ArraysViolinConfig | None = None,
    ) -> None:

        # ── Type checks ───────────────────────────────────────────────
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR_PREFIX}: cohort_timeline must be a CohortTimeline, "
                f"got {type(cohort_timeline).__name__}"
            )

        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(
                f"{_ERROR_PREFIX}: identity must be a non-empty string, "
                f"got {identity!r}"
            )

        if config is None:
            config = ArraysViolinConfig()
        if not isinstance(config, ArraysViolinConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an ArraysViolinConfig, "
                f"got {type(config).__name__}"
            )

        # ── Validate required columns exist ───────────────────────────
        required = _required_cols(identity)
        missing  = required - set(cohort_timeline.data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: cohort_timeline is missing required columns "
                f"for identity {identity!r}: {sorted(missing)}. "
                f"Call CohortTimelineEpisodeAnalyzer(ct, {identity!r})"
                f".compute_coverage() first."
            )

        self._cohort_timeline = cohort_timeline
        self._identity        = identity
        self._config          = config
        self._n_total         = len(cohort_timeline)

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_total(self, path: str) -> None:
        """
        Two-violin plot: active_days vs inactive_days.
        Both include ALL entities — zero is valid and meaningful.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        validate_path(path, _ERROR_PREFIX)

        from eventus.visualizers.violins.episode_coverage_violin_plotter_utils import (
            build_total_arrays,
            apply_unit_conversion,
            resolve_divisor,
            build_tick_labels,
        )

        plot_order, arrays = build_total_arrays(
            self._cohort_timeline.data, self._identity
        )

        divisor = resolve_divisor(self._config.labels.units)
        arrays  = apply_unit_conversion(arrays, divisor)

        self._draw(
            path       = path,
            arrays     = arrays,
            plot_order = plot_order,
            title      = f"Active vs Inactive days — {self._identity}",
        )

    def plot_inactive_breakdown(self, path: str) -> None:
        """
        Up to three violin plots: inactive_days_before_first_episode,
        inactive_days_after_last_episode, inactive_days_middle.
        Each violin filtered to entities where that metric > 0.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        validate_path(path, _ERROR_PREFIX)

        from eventus.visualizers.violins.episode_coverage_violin_plotter_utils import (
            build_breakdown_arrays,
            apply_unit_conversion,
            resolve_divisor,
        )

        plot_order, arrays = build_breakdown_arrays(
            data           = self._cohort_timeline.data,
            identity       = self._identity,
            breakdown_cols = _BREAKDOWN_METRICS,
        )

        # Drop any metrics that came back empty (column missing in data)
        plot_order = [k for k in plot_order if len(arrays[k]) > 0]
        arrays     = {k: arrays[k] for k in plot_order}

        if not plot_order:
            raise ValueError(
                f"{_ERROR_PREFIX}: no breakdown metrics had any data > 0. "
                f"Cannot draw plot_inactive_breakdown()."
            )

        divisor = resolve_divisor(self._config.labels.units)
        arrays  = apply_unit_conversion(arrays, divisor)

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
        from eventus.visualizers.violins.episode_coverage_violin_plotter_utils import (
            build_tick_labels,
        )

        cfg      = self._config
        resolved = cfg.resolve(plot_order)

        # Override title if not set in config labels
        if not cfg.labels.title:
            import copy
            cfg = copy.copy(cfg)
            object.__setattr__(cfg, "labels", copy.copy(cfg.labels))
            cfg.labels.title = title

        # Build plotter — validation and drawing handled entirely there
        plotter = ArraysViolinPlotter(arrays, cfg)

        # Swap in coverage-specific tick labels (adds % of cohort)
        # by monkey-patching plot_order-aware labels after construction
        # We draw manually to inject custom tick labels
        import matplotlib.pyplot as plt

        canvas = cfg.canvas
        scfg   = cfg.style
        pcfg   = cfg.percentiles
        lcfg   = cfg.labels
        axcfg  = cfg.axes

        configured = [k for k in cfg.plot_order if k in arrays]
        extras     = [k for k in arrays if k not in cfg.plot_order]
        final_order = configured + extras

        from eventus.visualizers.violins.arrays_violin_plotter_utils import (
            apply_y_bounds,
            compute_widths,
            draw_box,
            draw_percentile_lines,
            draw_points,
            draw_violin_body,
        )

        widths = compute_widths(arrays, final_order)
        sizes  = {k: len(arrays[k]) for k in final_order}

        fig, ax = plt.subplots(figsize=canvas.figsize)

        for i, key in enumerate(final_order):
            arr   = arrays[key]
            color = resolved[key].color
            width = widths[key]

            draw_violin_body(ax, arr, i, width, color, scfg.bandwidth)
            if scfg.show_box:
                draw_box(ax, arr, i, color)
            if scfg.show_points:
                draw_points(ax, arr, i, width, color, scfg.point_alpha, scfg.point_size)
            if pcfg.show:
                draw_percentile_lines(ax, arr, i, width, pcfg, canvas.font_size)

        apply_y_bounds(ax, axcfg)

        # Coverage-specific tick labels: label + n + % of cohort
        tick_labels = build_tick_labels(final_order, arrays, self._n_total, resolved)
        ax.set_xticks(range(len(final_order)))
        ax.set_xticklabels(tick_labels, fontsize=canvas.font_size - 1)
        ax.set_xlim(-0.5, len(final_order) - 0.5)

        if lcfg.title:
            ax.set_title(lcfg.title, fontsize=canvas.font_size + 1)
        if lcfg.ylabel:
            ax.set_ylabel(lcfg.ylabel, fontsize=canvas.font_size)
        elif lcfg.units:
            ax.set_ylabel(lcfg.units, fontsize=canvas.font_size)
        if lcfg.xlabel:
            ax.set_xlabel(lcfg.xlabel, fontsize=canvas.font_size)

        ax.tick_params(axis="y", labelsize=canvas.font_size - 1)

        fig.tight_layout()
        save_figure(fig, path, canvas.dpi)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EpisodeCoverageViolinPlotter(\n"
            f"  identity  : {self._identity!r}\n"
            f"  entities  : {self._n_total:,}\n"
            f"  units     : {self._config.labels.units!r}\n"
            f")"
        )
