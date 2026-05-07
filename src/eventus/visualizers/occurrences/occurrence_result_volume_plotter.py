"""
occurrence_result_volume_plotter.py
OccurrenceResultVolumePlotter — plots for OccurrenceResultVolume.

Plot methods
------------
plot_histogram(path)        — distribution of N per entity
plot_prevalence_bar(path)   — % with any / % with multiple / % with none
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.occurrence_result_volume import OccurrenceResultVolume
from .occurrence_result_plotter_config import OccurrenceResultVolumeConfig
from . import occurrence_result_plotter_utils        as shared_utils
from . import occurrence_result_volume_plotter_utils as volume_utils

_ERROR = "[OccurrenceResultVolumePlotter] Error"


class OccurrenceResultVolumePlotter:
    """
    I plot occurrence volume statistics from an OccurrenceResultVolume.

    Parameters
    ----------
    volume : OccurrenceResultVolume
    config : OccurrenceResultVolumeConfig | None
        Plot configuration. Uses build_with_defaults() if not provided.
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
            config = OccurrenceResultVolumeConfig.build_with_defaults()
        if not isinstance(config, OccurrenceResultVolumeConfig):
            raise TypeError(
                f"{_ERROR} config must be an OccurrenceResultVolumeConfig, "
                f"got {type(config).__name__}"
            )
        self._volume = volume
        self._config = config

    # ------------------------------------------------------------------ #
    # Plot methods
    # ------------------------------------------------------------------ #

    def plot_histogram(self, path: str) -> None:
        """
        Plot the distribution of N occurrences per entity.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg      = self._config
        data     = self._volume.data
        n_series = data["n"].astype(float)

        fig, ax = plt.subplots(figsize=cfg.histogram.style.figsize)

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = f"Occurrence count distribution — {self._volume.identity}",
        )

        shared_utils.draw_histogram(
            ax     = ax,
            series = n_series,
            cfg    = cfg.histogram,
        )

        xlabel = cfg.histogram.xlabel or f"Number of {self._volume.identity} occurrences"
        ylabel = cfg.histogram.ylabel or "Entities"
        ax.set_xlabel(xlabel, fontsize=cfg.general.font_size)
        ax.set_ylabel(ylabel, fontsize=cfg.general.font_size)

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

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
        data       = self._volume.data
        prevalence = volume_utils.compute_prevalence(
            n_col   = data["n"],
            n_total = self._volume.n_entities,
        )

        fig, ax = plt.subplots(figsize=cfg.general.figsize or [8, 5])

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = f"Occurrence prevalence — {self._volume.identity}",
        )

        volume_utils.draw_prevalence_bar(
            ax         = ax,
            prevalence = prevalence,
            bar_cfg    = cfg.bar,
            font_size  = cfg.general.font_size,
            identity   = self._volume.identity,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultVolumePlotter(\n"
            f"  identity : '{self._volume.identity}'\n"
            f"  entities : {self._volume.n_entities:,}\n"
            f")"
        )
