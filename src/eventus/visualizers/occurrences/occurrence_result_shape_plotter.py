"""
occurrence_result_shape_plotter.py
OccurrenceResultShapePlotter — plots for OccurrenceResultShape.

Plot methods
------------
plot_fingerprint(path)      — burstiness vs memory scatter
plot_center_of_mass(path)   — histogram of center_of_mass
plot_density(path)          — histogram of density
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.intermediates.occurrence_result_shape import OccurrenceResultShape
from .occurrence_result_plotter_config import OccurrenceResultShapeConfig
from . import occurrence_result_plotter_utils       as shared_utils
from . import occurrence_result_shape_plotter_utils as shape_utils

_ERROR = "[OccurrenceResultShapePlotter] Error"


class OccurrenceResultShapePlotter:
    """
    I plot occurrence shape statistics from an OccurrenceResultShape.

    Parameters
    ----------
    shape  : OccurrenceResultShape
    config : OccurrenceResultShapeConfig | None
        Plot configuration. Uses build_with_defaults() if not provided.
    """

    _shape: OccurrenceResultShape
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
            config = OccurrenceResultShapeConfig.build_with_defaults()
        if not isinstance(config, OccurrenceResultShapeConfig):
            raise TypeError(
                f"{_ERROR} config must be an OccurrenceResultShapeConfig, "
                f"got {type(config).__name__}"
            )
        self._shape  = shape
        self._config = config

    # ------------------------------------------------------------------ #
    # Plot methods
    # ------------------------------------------------------------------ #

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

        fig, ax = plt.subplots(figsize=cfg.general.figsize or [8, 7])

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = (
                f"Behavioral fingerprint — {self._shape.identity}\n"
                f"Burstiness vs Memory"
            ),
        )

        shape_utils.draw_fingerprint_scatter(
            ax          = ax,
            burstiness  = data["burstiness"],
            memory      = data["memory"],
            scatter_cfg = cfg.scatter,
            font_size   = cfg.general.font_size,
            n_eligible  = n_eligible,
            n_total     = self._shape.n_entities,
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

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

        fig, ax = plt.subplots(
            figsize=cfg.general.figsize or cfg.center_of_mass.style.figsize
        )

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = (
                f"Center of mass — {self._shape.identity}\n"
                f"0 = front-loaded  ·  0.5 = uniform  ·  1 = back-loaded"
            ),
        )

        shape_utils.draw_distribution_histogram(
            ax            = ax,
            series        = data["center_of_mass"],
            histogram_cfg = cfg.center_of_mass,
            font_size     = cfg.general.font_size,
            n_total       = self._shape.n_entities,
            auto_xlabel   = "Center of mass (0=front-loaded, 1=back-loaded)",
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

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

        fig, ax = plt.subplots(
            figsize=cfg.general.figsize or cfg.density.style.figsize
        )

        shared_utils.apply_general_config(
            fig             = fig,
            axes            = ax,
            style           = cfg.general.style,
            font_size       = cfg.general.font_size,
            title_font_size = cfg.general.title_font_size,
            title           = cfg.general.title,
            auto_title      = f"Occurrence density — {self._shape.identity}",
        )

        shape_utils.draw_distribution_histogram(
            ax            = ax,
            series        = data["density"],
            histogram_cfg = cfg.density,
            font_size     = cfg.general.font_size,
            n_total       = self._shape.n_entities,
            auto_xlabel   = "Density (occurrences per day)",
        )

        fig.tight_layout()
        shared_utils.save_figure(fig, path, cfg.general.dpi)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"OccurrenceResultShapePlotter(\n"
            f"  identity       : '{self._shape.identity}'\n"
            f"  entities       : {self._shape.n_entities:,}\n"
            f"  n_with_shape   : {self._shape.n_with_shape:,}\n"
            f"  n_with_memory  : {self._shape.n_with_memory:,}\n"
            f")"
        )
