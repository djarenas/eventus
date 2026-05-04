"""
events_duration_violin_plotter.py
EventsDurationViolinPlotter — violin plot visualization of event durations,
optionally stratified by a column in events.data.

This class is pure orchestration. All computation lives in
events_duration_violin_plotter_utils.py.
"""
from __future__ import annotations
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ERROR_PREFIX = "[EventsDurationViolinPlotter] Error"


class EventsDurationViolinPlotter:
    """
    Violin plot visualization of event durations from a validated Events object.

    One violin per category. Violin width is scaled by sqrt(n) relative
    to the largest category. Optional total violin ('all_data') is always
    plotted first.

    Parameters
    ----------
    events : Events
        A validated Events object.
    stratify_by : str | None
        Column in events.data to stratify by. Must exist in events.data.
        If None, only the total violin is drawn (requires all_data in config).
    config : ViolinConfig | None
        Plot configuration. Uses ViolinConfig.build_with_defaults()
        if not provided.

    Examples
    --------
    >>> config  = ViolinConfig.build_from_yaml("violin_config.yaml")
    >>> plotter = EventsDurationViolinPlotter(events, stratify_by="hospital_id", config=config)
    >>> plotter.plot("duration_violin.png")

    >>> # No stratification — total only
    >>> plotter = EventsDurationViolinPlotter(events, config=config)
    >>> plotter.plot("duration_violin.png")
    """

    def __init__(
        self,
        events,
        config = None,
    ) -> None:
        from eventus.data_objects.events import Events
        from .event_duration_violin_config import EventDurationViolinConfig as ViolinConfig

        # ── Type checks ───────────────────────────────────────────────
        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR_PREFIX}: events must be an Events object, "
                f"got {type(events).__name__}"
            )

        if config is None:
            config = ViolinConfig.build_with_defaults()
        if not isinstance(config, ViolinConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a ViolinConfig object, "
                f"got {type(config).__name__}"
            )

        # ── Validate stratify_by and categories ──────────────────────
        stratify_by = config.stratify_by

        # Categories defined without a stratify_by is meaningless
        if stratify_by is None and config.category_keys_non_total:
            raise ValueError(
                f"{_ERROR_PREFIX}: config has categories "
                f"{config.category_keys_non_total} but stratify_by is None — "
                f"no column to look them up in. "
                f"Set stratify_by in the config or remove the categories."
            )

        # Must have something to plot
        if stratify_by is None and not config.has_total:
            raise ValueError(
                f"{_ERROR_PREFIX}: config has no stratify_by and no all_data "
                f"entry — nothing to plot. "
                f"Add all_data to stratify or set stratify_by in the config."
            )

        # Validate column exists in data
        if stratify_by is not None:
            if stratify_by not in events.data.columns:
                raise ValueError(
                    f"{_ERROR_PREFIX}: stratify_by column '{stratify_by}' not "
                    f"found in events.data. "
                    f"Available columns: {sorted(events.data.columns.tolist())}"
                )
            if "all_data" in events.data[stratify_by].astype(str).values:
                raise ValueError(
                    f"{_ERROR_PREFIX}: 'all_data' is a reserved key and "
                    f"cannot appear as a value in the '{stratify_by}' column. "
                    f"Rename that category in your data before plotting."
                )

        # ── Validate category count ───────────────────────────────────
        n_cats = len(config.category_keys)
        if n_cats > config.style.max_categories:
            raise ValueError(
                f"{_ERROR_PREFIX}: config has {n_cats} categories but "
                f"style.max_categories={config.style.max_categories}. "
                f"Categories: {config.category_keys}. "
                f"Increase max_categories in config or reduce categories."
            )

        # ── Validate config has something to plot ─────────────────────
        if not config.has_total and not config.category_keys:
            raise ValueError(
                f"{_ERROR_PREFIX}: config has no categories and no all_data "
                f"entry — nothing to plot. Add at least one entry to stratify."
            )

        if not config.has_total and stratify_by is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: stratify_by is None but config has no "
                f"all_data entry. Either set stratify_by or add all_data "
                f"to the stratify section."
            )

        self._events  = events
        self._config  = config

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """
        Save the violin plot to a file.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        """
        from .events_duration_violin_plotter_utils import (
            prepare_data, compute_widths, draw_violins,
        )
        from eventus.analyzers.event_duration_analyzer import EventDurationAnalyzer

        self._validate_path(path)

        cfg    = self._config
        scfg   = cfg.style
        pcfg   = cfg.percentiles
        lcfg   = cfg.labels

        # ── Compute durations ─────────────────────────────────────────
        df = EventDurationAnalyzer(
            events      = self._events,
            stratify_by = self._config.stratify_by,
        ).calc()

        duration_col = "duration_days"
        entity_col   = self._events.semantics.entity_id_col

        # ── Convert duration unit ─────────────────────────────────────
        divisor = lcfg.divisor
        if divisor != 1.0:
            df[duration_col] = df[duration_col] / divisor

        # ── Prepare per-category arrays ───────────────────────────────
        if self._config.stratify_by is not None:
            plot_order, arrays = prepare_data(
                data         = df,
                entity_col   = entity_col,
                duration_col = duration_col,
                stratify_by  = "stratify_col",
                config       = cfg,
            )
        else:
            # No stratify_by — total only
            plot_order = ["all_data"]
            arrays     = {"all_data": df[duration_col].dropna().values}

        if not arrays:
            raise ValueError(
                f"{_ERROR_PREFIX}: no data to plot after filtering "
                f"to configured categories."
            )

        # ── Compute widths ────────────────────────────────────────────
        widths = compute_widths(arrays, plot_order)

        # ── Figure ────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=scfg.figsize)

        # Build colors dict
        colors = {
            key: (cfg.stratify[key].color if key in cfg.stratify else "#AAAAAA")
            for key in plot_order
        }

        draw_violins(
            ax          = ax,
            plot_order  = plot_order,
            arrays      = arrays,
            widths      = widths,
            colors      = colors,
            show_box    = scfg.show_box,
            show_points = scfg.show_points,
            point_alpha = scfg.point_alpha,
            point_size  = scfg.point_size,
            pcfg        = pcfg,
        )

        # ── X axis ticks and labels ───────────────────────────────────
        tick_labels = []
        for key in plot_order:
            cat_cfg = cfg.stratify.get(key)
            n       = len(arrays[key])
            label   = (cat_cfg.label if cat_cfg and cat_cfg.label else key)
            tick_labels.append(f"{label}\n(n={n:,})")

        ax.set_xticks(range(len(plot_order)))
        ax.set_xticklabels(tick_labels, fontsize=10)
        ax.set_xlim(-0.5, len(plot_order) - 0.5)

        # ── Labels ────────────────────────────────────────────────────
        title = lcfg.title
        if title is None:
            identity = self._events.semantics.identity
            if identity:
                title = f"Duration — {identity}"

        if title:
            ax.set_title(title, fontsize=12)

        ax.set_ylabel(lcfg.resolved_ylabel, fontsize=10)

        xlabel = lcfg.xlabel
        if xlabel is None and self._config.stratify_by:
            xlabel = self._config.stratify_by
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=10)

        ax.tick_params(axis="y", labelsize=9)

        # ── Y axis bounds ─────────────────────────────────────────────
        if scfg.y_min is not None or scfg.y_max is not None:
            ax.set_ylim(
                bottom = scfg.y_min,
                top    = scfg.y_max,
            )

        # ── Save ──────────────────────────────────────────────────────
        fig.tight_layout()
        fig.savefig(path, dpi=scfg.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Validation and dunder
    # ------------------------------------------------------------------ #

    def _validate_path(self, path: str) -> None:
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
                f"Use .png, .jpg, or .jpeg"
            )

    def __repr__(self) -> str:
        return (
            f"EventsDurationViolinPlotter(\n"
            f"  events       : {len(self._events):,} rows\n"
            f"  identity     : {self._events.semantics.identity!r}\n"
            f"  stratify_by  : {self._config.stratify_by!r}\n"
            f"  categories   : {self._config.category_keys}\n"
            f"  has_total    : {self._config.has_total}\n"
            f")"
        )
