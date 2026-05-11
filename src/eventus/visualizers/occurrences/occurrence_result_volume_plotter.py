"""
occurrence_result_volume_plotter.py
OccurrenceResultVolumePlotter — plots for OccurrenceResultVolume.

Plot methods
------------
plot_prevalence_bar(path)         — % with any / % with multiple / % with none
plot_count_distribution_bar(path) — discrete n=0, n=1, ... n=max_n+ breakdown
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.occurrence_result_volume import OccurrenceResultVolume
from eventus.visualizers.configs.occurrence_result_volume_config import OccurrenceResultVolumeConfig
from eventus.visualizers.occurrences import occurrence_result_plotter_utils        as shared_utils
from eventus.visualizers.occurrences import occurrence_result_volume_plotter_utils as volume_utils

_ERROR = "[OccurrenceResultVolumePlotter]"


class OccurrenceResultVolumePlotter:
    """
    I plot occurrence volume statistics from an OccurrenceResultVolume.

    Parameters
    ----------
    volume : OccurrenceResultVolume
    config : OccurrenceResultVolumeConfig | None
        Plot configuration. Defaults to OccurrenceResultVolumeConfig() if not provided.
    """

    _volume: OccurrenceResultVolume
    _config: OccurrenceResultVolumeConfig

    def __init__(
        self,
        volume: OccurrenceResultVolume,
        config: OccurrenceResultVolumeConfig | None = None,
    ) -> None:
        if not isinstance(volume, OccurrenceResultVolume):
            raise TypeError(
                f"{_ERROR} volume must be an OccurrenceResultVolume, "
                f"got {type(volume).__name__}"
            )
        if config is None:
            config = OccurrenceResultVolumeConfig()
        if not isinstance(config, OccurrenceResultVolumeConfig):
            raise TypeError(
                f"{_ERROR} config must be an OccurrenceResultVolumeConfig, "
                f"got {type(config).__name__}"
            )
        self._volume = volume
        self._config = config

    # ── Plot methods ──────────────────────────────────────────────────────────

    def plot_prevalence_bar(self, path: str) -> None:
        """
        Plot % of cohort with any / multiple / no occurrences.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg        = self._config
        prevalence = volume_utils.compute_prevalence(
            n_col   = self._volume.data["n"],
            n_total = self._volume.n_entities,
        )

        fig, ax = plt.subplots(figsize=cfg.canvas.figsize)

        shared_utils.apply_style(
            fig        = fig,
            axes       = ax,
            canvas     = cfg.canvas,
            labels     = cfg.bar.labels,
            auto_title = f"Occurrence prevalence — {self._volume.identity}",
        )

        volume_utils.draw_prevalence_bar(
            ax         = ax,
            prevalence = prevalence,
            bar_cfg    = cfg.bar,
            font_size  = cfg.canvas.font_size,
            identity   = self._volume.identity,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    def plot_count_distribution_bar(self, path: str) -> None:
        """
        Plot a discrete breakdown of n=0, n=1, ... n=max_n+ occurrences per entity.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg     = self._config
        buckets = volume_utils.compute_count_distribution(
            n_col   = self._volume.data["n"],
            n_total = self._volume.n_entities,
            max_n   = cfg.count_bar.max_n,
        )

        fig, ax = plt.subplots(figsize=cfg.canvas.figsize)

        shared_utils.apply_style(
            fig        = fig,
            axes       = ax,
            canvas     = cfg.canvas,
            labels     = cfg.count_bar.labels,
            auto_title = f"Occurrence count breakdown — {self._volume.identity}",
        )

        volume_utils.draw_count_distribution_bar(
            ax        = ax,
            buckets   = buckets,
            n_col     = self._volume.data["n"],
            n_total   = self._volume.n_entities,
            bar_cfg   = cfg.count_bar,
            font_size = cfg.canvas.font_size,
            identity  = self._volume.identity,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultVolumePlotter(\n"
            f"  identity : '{self._volume.identity}'\n"
            f"  entities : {self._volume.n_entities:,}\n"
            f")"
        )
