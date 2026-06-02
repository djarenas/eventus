"""
event_result_shape_plotter.py
EventResultShapePlotter — plots for EventResultShape.

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

from eventus.intermediates.event_result_shape import EventResultShape
from eventus.visualizers.configs.event_result_shape_config import EventResultShapeConfig
from eventus.visualizers.events import event_result_plotter_utils       as shared_utils
from eventus.visualizers.events import event_result_shape_plotter_utils as shape_utils

_ERROR = "[EventResultShapePlotter]"


class EventResultShapePlotter:
    """
    I plot event shape statistics from an EventResultShape.

    Parameters
    ----------
    shape  : EventResultShape
    config : EventResultShapeConfig | None
        Plot configuration. Defaults to EventResultShapeConfig() if not provided.
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _shape:  EventResultShape       # validated shape result input
    _config: EventResultShapeConfig # plot configuration

    def __init__(
        self,
        shape:  EventResultShape,
        config: EventResultShapeConfig | None = None,
    ) -> None:
        if not isinstance(shape, EventResultShape):
            raise TypeError(
                f"{_ERROR} shape must be an EventResultShape, "
                f"got {type(shape).__name__}"
            )
        if config is None:
            config = EventResultShapeConfig()
        if not isinstance(config, EventResultShapeConfig):
            raise TypeError(
                f"{_ERROR} config must be an EventResultShapeConfig, "
                f"got {type(config).__name__}"
            )
        self._shape  = shape
        self._config = config

    # ── Plot methods ──────────────────────────────────────────────────────────

    def plot_fingerprint(self, path: str) -> None:
        """
        Plot burstiness vs memory behavioral fingerprint scatter.

        Only entities with n >= 4 events appear — memory requires
        at least 3 inter-event gaps. The eligible count is shown
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
        Entities with 0 events (NaN center_of_mass) are excluded.

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
        Plot distribution of event density across the cohort.

        density = n / obs_duration_days per entity.
        Entities with 0 events (NaN density) are excluded.

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
            auto_title = f"Event density — {self._shape.identity}",
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

    def plot_mean_gap_violin(
        self,
        path:          str,
        violin_config: "ArraysViolinConfig | None" = None,
    ) -> None:
        """
        Plot distribution of mean inter-event gap as a violin.

        Only entities with at least 2 events (n_with_gaps) appear —
        mean_gap requires at least one gap. Entities with fewer than 2
        events have NaN mean_gap and are excluded automatically.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        violin_config : ArraysViolinConfig | None
            Visual configuration for the violin plot. If None, sensible
            defaults are used — one teal violin, days on y-axis.
        """
        from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
        from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter

        shared_utils.validate_path(path, _ERROR)

        mean_gap = self._shape.data["mean_gap"].dropna()

        if len(mean_gap) < 2:
            raise ValueError(
                f"{_ERROR} plot_mean_gap_violin() requires at least 2 entities "
                f"with valid mean_gap. Got {len(mean_gap)}. "
                f"Ensure members have at least 2 events."
            )

        if violin_config is None:
            from eventus.visualizers.configs.category_config import CategoryConfig
            from eventus.visualizers.configs.base_plot_config import AxisLabels
            from eventus.visualizers.configs.percentiles_config import PercentilesConfig
            violin_config = ArraysViolinConfig.build_from_dict({
                "canvas": {
                    "figsize":    [6, 8],
                    "dpi":        120,
                    "font_size":  12,
                },
                "labels": {
                    "title":  f"Mean gap between events — {self._shape.identity}",
                    "ylabel": "days",
                },
                "axes": {"y_min": 0},
                "style": {
                    "bandwidth":   "scott",
                    "show_box":    True,
                    "show_points": False,
                },
                "percentiles": {
                    "show":        True,
                    "values":      [25, 50, 75],
                    "linestyle":   "dashed",
                    "show_labels": True,
                },
                "categories": {
                    "mean_gap": {"color": "#028090", "label": "mean gap (days)"},
                },
            })

        arrays = {"mean_gap": mean_gap.values}
        ArraysViolinPlotter(arrays, violin_config).plot(path)

    def plot_mean_gap_violin_stratified(
        self,
        path:             str,
        cohort_timeline:  object,
        stratify_by:      str,
        violin_config:    "ArraysViolinConfig | None" = None,
        max_groups:       int = 5,
    ) -> None:
        """
        Plot mean inter-event gap as a stratified violin, grouped
        by a descriptor column carried in the CohortTimeline.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        cohort_timeline : CohortTimeline
            The enriched CohortTimeline carrying the descriptor column.
            Must contain evt_{identity}_{stratify_by}.
        stratify_by : str
            Descriptor column name to stratify by e.g. "icd10_condition".
            Must be declared in EventSemantics.descriptor_cols with
            timeline != "none".
        violin_config : ArraysViolinConfig | None
            Visual configuration. If None, sensible defaults are used.
        max_groups : int
            Maximum number of groups allowed before raising. Default 5.
            Override by declaring explicit categories in violin_config.
        """
        from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
        from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter

        shared_utils.validate_path(path, _ERROR)

        # ── Get descriptor series from CohortTimeline ─────────────────────
        descriptor = cohort_timeline.get_event_descriptor(
            self._shape.identity, stratify_by
        )

        # ── Join mean_gap with descriptor on entity ───────────────────────
        entity_col  = self._shape.entity_col
        shape_data  = self._shape.data[[entity_col, "mean_gap"]].copy()
        ct_data     = cohort_timeline.data[[entity_col]].copy()
        ct_data[stratify_by] = descriptor.values

        merged = shape_data.merge(ct_data, on=entity_col, how="left")
        merged = merged[merged["mean_gap"].notna()].copy()

        # ── Get unique groups ─────────────────────────────────────────────
        unique_groups = sorted(merged[stratify_by].dropna().unique())

        # If violin_config declares explicit categories, use those
        # Otherwise validate group count
        if violin_config is None or not violin_config.categories:
            if len(unique_groups) > max_groups:
                raise ValueError(
                    f"{_ERROR} plot_mean_gap_violin_stratified() found "
                    f"{len(unique_groups)} unique groups in '{stratify_by}': "
                    f"{unique_groups[:10]}{'...' if len(unique_groups) > 10 else ''}. "
                    f"This exceeds max_groups={max_groups}. "
                    f"Declare explicit categories in violin_config or increase "
                    f"max_groups."
                )
            groups = unique_groups
        else:
            groups = list(violin_config.categories.keys())

        # ── Build arrays dict ─────────────────────────────────────────────
        arrays = {}
        for group in groups:
            vals = merged[merged[stratify_by] == group]["mean_gap"].values
            if len(vals) >= 2:
                arrays[group] = vals

        if not arrays:
            raise ValueError(
                f"{_ERROR} plot_mean_gap_violin_stratified(): no groups had "
                f"at least 2 valid mean_gap values. Check that members have "
                f"at least 2 events and that '{stratify_by}' values match "
                f"the declared groups."
            )

        # ── Build default config if needed ────────────────────────────────
        if violin_config is None:
            violin_config = ArraysViolinConfig.build_from_dict({
                "canvas": {"figsize": [max(6, len(arrays) * 2), 8],
                           "dpi": 120, "font_size": 12},
                "labels": {
                    "title":  f"Mean gap by {stratify_by} — {self._shape.identity}",
                    "ylabel": "days",
                },
                "axes": {"y_min": 0},
                "style": {"bandwidth": "scott", "show_box": True},
                "percentiles": {"show": True, "values": [25, 50, 75],
                                "linestyle": "dashed", "show_labels": True},
                "categories": {
                    g: {"color": ["#028090","#E05C40","#6B4FA0",
                                  "#F0A500","#2E86AB"][i % 5]}
                    for i, g in enumerate(arrays.keys())
                },
            })

        ArraysViolinPlotter(arrays, violin_config).plot(path)

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"EventResultShapePlotter(\n"
            f"  identity      : '{self._shape.identity}'\n"
            f"  entities      : {self._shape.n_entities:,}\n"
            f"  n_with_gaps   : {self._shape.n_with_gaps:,}\n"
            f"  n_with_shape  : {self._shape.n_with_shape:,}\n"
            f"  n_with_memory : {self._shape.n_with_memory:,}\n"
            f"  methods       : plot_fingerprint, plot_center_of_mass, "
            f"plot_density, plot_mean_gap_violin, plot_mean_gap_violin_stratified\n"
            f")"
        )
