"""
events_duration_plotter.py
EventsDurationPlotter — visualization of event durations.

Takes an Events object and produces duration plots.
Currently supports histograms. Violin plots planned for future release.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ERROR_PREFIX = "[EventsDurationPlotter] Error"
  

class EventsDurationPlotter:
    """
    Visualization of event durations from a validated Events object.

    Creates and holds the plotter — then call plot methods to produce
    specific visualizations. Each plot method accepts its own config,
    so the same plotter can produce multiple plot types without
    rebuilding.

    Parameters
    ----------
    events : Events
        A validated Events object.
    stratify_by : str | None
        Column in events.data to stratify by. Must exist in events.data.
        Nulls filled with 'missing'. Max categories controlled by
        HistogramConfig.stratification.max_categories. Default None.

    Examples
    --------
    >>> plotter = EventsDurationPlotter(events)
    >>> plotter.plot_histogram(
    ...     config = HistogramConfig.build_with_defaults(),
    ...     path   = "duration.png"
    ... )

    >>> # Stratified
    >>> plotter = EventsDurationPlotter(events, stratify_by="hospital_id")
    >>> plotter.plot_histogram(
    ...     config = HistogramConfig.build_from_yaml("hist_config.yaml"),
    ...     path   = "duration_by_hospital.png"
    ... )
    """

    def __init__(
        self,
        events,
        stratify_by: str | None = None,
    ) -> None:
        from eventus.data_objects.events import Events

        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR_PREFIX}: events must be an Events object, "
                f"got {type(events).__name__}"
            )
        if stratify_by is not None and not isinstance(stratify_by, str):
            raise TypeError(
                f"{_ERROR_PREFIX}: stratify_by must be a string or None, "
                f"got {type(stratify_by).__name__}"
            )

        self._events      = events
        self._stratify_by = stratify_by

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_histogram(self, path: str, config=None) -> None:
        """
        Plot a histogram of event durations.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
        config : HistogramConfig | None
            Histogram configuration. Uses HistogramConfig.build_with_defaults()
            if not provided.
        """
        from .histogram_config import HistogramConfig
        from eventus.analyzers.event_duration_analyzer import EventDurationAnalyzer

        self._validate_path(path)

        if config is None:
            config = HistogramConfig.build_with_defaults()
        if not isinstance(config, HistogramConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a HistogramConfig object, "
                f"got {type(config).__name__}"
            )

        # Run analyzer internally
        df = EventDurationAnalyzer(
            events         = self._events,
            stratify_by    = self._stratify_by,
            max_categories = config.stratification.max_categories,
        ).calc()

        is_stratified = "stratify_col" in df.columns

        if is_stratified:
            style = config.stratification.style
            if style == "overlay":
                self._plot_overlay(df, config, path)
            else:
                self._plot_facet(df, config, path)
        else:
            self._plot_single(df, config, path)

    def plot_violin(self, path: str, config=None) -> None:
        """
        Plot a violin plot of event durations.
        Planned for a future release of eventus.
        """
        raise NotImplementedError(
            f"{_ERROR_PREFIX}: plot_violin() is planned for a future "
            f"release of eventus. Use plot_histogram() for now."
        )

    # ------------------------------------------------------------------ #
    # Plot implementations
    # ------------------------------------------------------------------ #

    def _plot_single(self, df: pd.DataFrame, config, path: str) -> None:
        """Plain histogram — no stratification."""
        data = df["duration_days"].dropna()
        fig, ax = plt.subplots(figsize=config.style.figsize)

        bins = self._resolve_bins(data, config)
        ax.hist(
            data,
            bins      = bins,
            color     = config.style.color,
            edgecolor = config.style.edgecolor,
            alpha     = config.style.alpha,
        )

        self._add_percentile_lines(ax, data, config)
        self._apply_labels(ax, data, config)

        fig.tight_layout()
        fig.savefig(path, dpi=config.style.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    def _plot_overlay(self, df: pd.DataFrame, config, path: str) -> None:
        """Stratified histogram — all categories overlapping on one axes."""
        categories = sorted(df["stratify_col"].unique())
        colors     = config.stratification.resolve_colors(categories)
        all_data   = df["duration_days"].dropna()
        bins       = self._resolve_bins(all_data, config)

        fig, ax = plt.subplots(figsize=config.style.figsize)

        for cat in categories:
            subset = df[df["stratify_col"] == cat]["duration_days"].dropna()
            ax.hist(
                subset,
                bins      = bins,
                color     = colors[cat],
                edgecolor = config.style.edgecolor,
                alpha     = 0.5,
                label     = f"{cat} (n={len(subset):,})",
            )

        self._add_percentile_lines(ax, all_data, config)
        self._apply_labels(ax, all_data, config)
        ax.legend(fontsize=9, frameon=False, loc="upper right")

        fig.tight_layout()
        fig.savefig(path, dpi=config.style.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    def _plot_facet(self, df: pd.DataFrame, config, path: str) -> None:
        """Stratified histogram — one subplot per category."""
        categories = sorted(df["stratify_col"].unique())
        colors     = config.stratification.resolve_colors(categories)
        n_cats     = len(categories)
        all_data   = df["duration_days"].dropna()
        bins       = self._resolve_bins(all_data, config)

        n_cols = min(2, n_cats)
        n_rows = int(np.ceil(n_cats / n_cols))
        fw, fh = config.style.figsize
        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize  = (fw * n_cols / 2, fh * n_rows / 2),
            sharex   = True,
            squeeze  = False,
        )

        fs = 10
        for idx, cat in enumerate(categories):
            row, col = divmod(idx, n_cols)
            ax       = axes[row][col]
            subset   = df[df["stratify_col"] == cat]["duration_days"].dropna()

            ax.hist(
                subset,
                bins      = bins,
                color     = colors[cat],
                edgecolor = config.style.edgecolor,
                alpha     = config.style.alpha,
            )

            self._add_percentile_lines(ax, subset, config)
            ax.set_title(f"{cat}  (n={len(subset):,})", fontsize=fs)
            ax.set_xlabel(
                config.labels.xlabel or "Duration (days)", fontsize=fs - 1
            )
            ax.set_ylabel(config.labels.ylabel, fontsize=fs - 1)
            ax.tick_params(labelsize=fs - 1)

        # Hide unused subplots
        for idx in range(n_cats, n_rows * n_cols):
            row, col = divmod(idx, n_cols)
            axes[row][col].set_visible(False)

        title = self._resolve_title(df, config)
        if title:
            fig.suptitle(title, fontsize=fs + 2, y=1.01)

        fig.tight_layout()
        fig.savefig(path, dpi=config.style.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _resolve_bins(self, data: pd.Series, config) -> np.ndarray:
        """Compute bin edges from config."""
        bc = config.bins

        if bc.type == "fixed_width":
            lo = bc.min if bc.min is not None else float(data.min())
            hi = bc.max if bc.max is not None else float(data.max())
            hi = min(hi, float(data.max()) + bc.width)
            return np.arange(lo, hi + bc.width, bc.width)

        elif bc.type == "percentile":
            pcts = np.linspace(0, 100, bc.n_bins + 1)
            return np.percentile(data.dropna(), pcts)

        elif bc.type == "log":
            lo = max(data.min(), 0.1)
            return np.logspace(np.log10(lo), np.log10(data.max()), bc.n_bins + 1)

        elif bc.type == "custom":
            return bc.edges

        return bc.n_bins

    def _add_percentile_lines(
        self, ax, data: pd.Series, config
    ) -> None:
        """Draw staggered percentile reference lines."""
        pcfg = config.percentile_lines
        if not pcfg.show:
            return

        ls_map  = {"dashed": "--", "dotted": ":", "solid": "-"}
        ls      = ls_map.get(pcfg.linestyle, "--")
        y_top   = ax.get_ylim()[1]
        y_steps = [0.97, 0.87, 0.77, 0.67, 0.57, 0.47]

        for i, p in enumerate(pcfg.values):
            val   = float(np.percentile(data.dropna(), p))
            y_pos = y_steps[i % len(y_steps)]
            ax.axvline(val, color=pcfg.color, linewidth=0.9, linestyle=ls)
            if pcfg.show_labels:
                ax.text(
                    val + 0.3, y_top * y_pos,
                    f"p{p}={val:.0f}d",
                    fontsize=8, color=pcfg.color,
                    va="top", ha="left",
                )

    def _apply_labels(self, ax, data: pd.Series, config) -> None:
        """Apply title, xlabel, ylabel, subtitle to axes."""
        lcfg = config.labels
        fs   = 10

        title = self._resolve_title(None, config)
        if title:
            ax.set_title(title, fontsize=fs + 2)

        ax.set_xlabel(lcfg.xlabel or "Duration (days)", fontsize=fs)
        ax.set_ylabel(lcfg.ylabel, fontsize=fs)
        ax.tick_params(labelsize=fs - 1)

        if lcfg.subtitle:
            ax.text(
                0.98, 0.97, lcfg.subtitle,
                transform=ax.transAxes, ha="right", va="top",
                fontsize=fs - 1, color="#555555",
            )

        ax.text(
            0.98, 0.87 if lcfg.subtitle else 0.97,
            f"n={len(data):,}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=fs - 1, color="#555555",
        )

    def _resolve_title(self, df, config) -> str | None:
        """Return title from config or auto-fill from identity."""
        if config.labels.title:
            return config.labels.title
        identity = self._events.semantics.identity
        if identity:
            return f"Duration — {identity}"
        return None

    def _validate_path(self, path: str) -> None:
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
                f"Use .png, .jpg, or .jpeg"
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventsDurationPlotter(\n"
            f"  events       : {len(self._events):,} rows\n"
            f"  identity     : {self._events.semantics.identity!r}\n"
            f"  stratify_by  : {self._stratify_by!r}\n"
            f")"
        )
