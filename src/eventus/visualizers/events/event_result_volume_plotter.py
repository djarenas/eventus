"""
event_result_volume_plotter.py
EventResultVolumePlotter — plots for EventResultVolume.

Plot methods
------------
plot_prevalence_bar(path)         — % with any / % with multiple / % with none
plot_count_distribution_bar(path) — discrete n=0, n=1, ... n=max_n+ breakdown
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.event_result_volume import EventResultVolume
from eventus.visualizers.configs.event_result_volume_config import EventResultVolumeConfig
from eventus.visualizers.events import event_result_plotter_utils        as shared_utils
from eventus.visualizers.events import event_result_volume_plotter_utils as volume_utils

_ERROR = "[EventResultVolumePlotter]"


class EventResultVolumePlotter:
    """
    I plot event volume statistics from an EventResultVolume.

    Parameters
    ----------
    volume : EventResultVolume
    config : EventResultVolumeConfig | None
        Plot configuration. Defaults to EventResultVolumeConfig() if not provided.
    """

    _volume: EventResultVolume
    _config: EventResultVolumeConfig

    def __init__(
        self,
        volume: EventResultVolume,
        config: EventResultVolumeConfig | None = None,
    ) -> None:
        if not isinstance(volume, EventResultVolume):
            raise TypeError(
                f"{_ERROR} volume must be an EventResultVolume, "
                f"got {type(volume).__name__}"
            )
        if config is None:
            config = EventResultVolumeConfig()
        if not isinstance(config, EventResultVolumeConfig):
            raise TypeError(
                f"{_ERROR} config must be an EventResultVolumeConfig, "
                f"got {type(config).__name__}"
            )
        self._volume = volume
        self._config = config

    # ── Plot methods ──────────────────────────────────────────────────────────

    def plot_prevalence_bar(self, path: str) -> None:
        """
        Plot % of cohort with any / multiple / no events.

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
            auto_title = f"Event prevalence — {self._volume.identity}",
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
        Plot a discrete breakdown of n=0, n=1, ... n=max_n+ events per entity.

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
            auto_title = f"Event count breakdown — {self._volume.identity}",
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
            f"EventResultVolumePlotter(\n"
            f"  identity : '{self._volume.identity}'\n"
            f"  entities : {self._volume.n_entities:,}\n"
            f")"
        )
