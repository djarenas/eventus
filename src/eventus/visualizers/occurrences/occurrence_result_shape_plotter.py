"""
occurrence_result_shape_plotter.py
OccurrenceResultShapePlotter — plots for OccurrenceResultShape.

Plot methods
------------
plot_fingerprint(path)    — burstiness vs memory scatter
plot_center_of_mass(path) — histogram of center_of_mass values
plot_density(path)        — histogram of density values
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.occurrence_result_shape import OccurrenceResultShape
from eventus.visualizers.configs.occurrence_result_shape_config import OccurrenceResultShapeConfig
from eventus.visualizers.occurrences import occurrence_result_plotter_utils       as shared_utils
from eventus.visualizers.occurrences import occurrence_result_shape_plotter_utils as shape_utils

_ERROR = "[OccurrenceResultShapePlotter]"


class OccurrenceResultShapePlotter:
    """
    I plot occurrence shape statistics from an OccurrenceResultShape.

    Parameters
    ----------
    shape  : OccurrenceResultShape
    config : OccurrenceResultShapeConfig | None
        Plot configuration. Defaults to OccurrenceResultShapeConfig() if not provided.
    """

    _shape:  OccurrenceResultShape
    _config: OccurrenceResultShapeConfig

    def __init__(
        self,
        shape:  OccurrenceResultShape,
        config: OccurrenceResultShapeConfig | None = None,
    ) -> None:
        if not isinstance(shape, OccurrenceResultShape):
            raise TypeError(
                f"{_ERROR} shape must be an OccurrenceResultShape, "
                f"got {type(shape).__name__}"
            )
        if config is None:
            config = OccurrenceResultShapeConfig()
        if not isinstance(config, OccurrenceResultShapeConfig):
            raise TypeError(
                f"{_ERROR} config must be an OccurrenceResultShapeConfig, "
                f"got {type(config).__name__}"
            )
        self._shape  = shape
        self._config = config

    # ── Plot methods ──────────────────────────────────────────────────────────

    def plot_fingerprint(self, path: str) -> None:
        """
        Plot burstiness vs memory behavioral fingerprint scatter.

        Only entities with n >= 4 occurrences appear — memory requires
        at least 3 inter-occurrence gaps. The eligible count is shown
        in the subplot title.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg  = self._config
        data = self._shape.data

        n_eligible = int(
            (data["burstiness"].notna() & data["memory"].notna()).sum()
        )

        fig, ax = plt.subplots(figsize=cfg.canvas.figsize)

        shared_utils.apply_style(
            fig        = fig,
            axes       = ax,
            canvas     = cfg.canvas,
            labels     = cfg.scatter.labels,
            auto_title = (
                f"Behavioral fingerprint — {self._shape.identity}\n"
                f"Burstiness vs Memory"
            ),
        )

        shape_utils.draw_fingerprint_scatter(
            ax          = ax,
            burstiness  = data["burstiness"],
            memory      = data["memory"],
            scatter_cfg = cfg.scatter,
            font_size   = cfg.canvas.font_size,
            n_eligible  = n_eligible,
            n_total     = self._shape.n_entities,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    def plot_center_of_mass(self, path: str) -> None:
        """
        Plot distribution of center_of_mass across the cohort.

        center_of_mass is normalized to [0, 1]:
        0 = front-loaded, 0.5 = uniform, 1 = back-loaded.
        Entities with 0 occurrences (NaN center_of_mass) are excluded.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg  = self._config
        data = self._shape.data

        fig, ax = plt.subplots(figsize=cfg.canvas.figsize)

        shared_utils.apply_style(
            fig        = fig,
            axes       = ax,
            canvas     = cfg.canvas,
            labels     = cfg.center_of_mass.labels,
            auto_title = (
                f"Center of mass — {self._shape.identity}\n"
                f"0 = front-loaded  ·  0.5 = uniform  ·  1 = back-loaded"
            ),
        )

        shape_utils.draw_distribution_histogram(
            ax            = ax,
            series        = data["center_of_mass"],
            histogram_cfg = cfg.center_of_mass,
            font_size     = cfg.canvas.font_size,
            n_total       = self._shape.n_entities,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    def plot_density(self, path: str) -> None:
        """
        Plot distribution of occurrence density across the cohort.

        density = n / obs_duration_days per entity.
        Entities with 0 occurrences (NaN density) are excluded.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        shared_utils.validate_path(path, _ERROR)

        cfg  = self._config
        data = self._shape.data

        fig, ax = plt.subplots(figsize=cfg.canvas.figsize)

        shared_utils.apply_style(
            fig        = fig,
            axes       = ax,
            canvas     = cfg.canvas,
            labels     = cfg.density.labels,
            auto_title = f"Occurrence density — {self._shape.identity}",
        )

        shape_utils.draw_distribution_histogram(
            ax            = ax,
            series        = data["density"],
            histogram_cfg = cfg.density,
            font_size     = cfg.canvas.font_size,
            n_total       = self._shape.n_entities,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.canvas.dpi)

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultShapePlotter(\n"
            f"  identity      : '{self._shape.identity}'\n"
            f"  entities      : {self._shape.n_entities:,}\n"
            f"  n_with_shape  : {self._shape.n_with_shape:,}\n"
            f"  n_with_memory : {self._shape.n_with_memory:,}\n"
            f")"
        )
