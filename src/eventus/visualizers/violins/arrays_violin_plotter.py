"""
arrays_violin_plotter.py
ArraysViolinPlotter — draw a violin plot from pre-built arrays.

Receives a {key: array-like} dict and an ArraysViolinConfig.
Knows nothing about where the arrays came from — that is the caller's
responsibility (e.g. DurationArrayBuilder, CoverageArrayBuilder).

All input validation happens in __init__. By the time plot() is called,
arrays are guaranteed to be clean 1-D float arrays with at least 2 finite
values each.

Plot order follows the order of categories defined in the config.
Keys present in arrays but absent from config.categories are appended
at the end and auto-assigned a color from the default palette.
"""
from __future__ import annotations

import pathlib
import warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig

_ERROR_PREFIX = "[ArraysViolinPlotter] Error"
_WARN_PREFIX  = "[ArraysViolinPlotter] Warning"

# Warn if more than this fraction of values are dropped during cleaning
_NAN_WARN_THRESHOLD = 0.20


class ArraysViolinPlotter:
    """
    Draw a violin plot from a pre-built {key: array-like} dict.

    Parameters
    ----------
    arrays : dict[str, array-like]
        One entry per violin. Keys must be non-empty strings.
        Values must be convertible to 1-D numeric arrays.
        NaN and inf values are dropped automatically.
    config : ArraysViolinConfig | None
        Plot configuration. Uses ArraysViolinConfig() defaults if not provided.

    Raises
    ------
    TypeError
        If arrays is not a dict, or config is the wrong type.
    ValueError
        If any key is not a non-empty string, any value cannot be converted
        to a numeric 1-D array, or any array has fewer than 2 finite values.

    Warns
    -----
    UserWarning
        If more than 20% of values are dropped from any array during cleaning.
        If all values in an array are identical (violin degenerates to a line).
        If config.plot_order references keys not present in arrays.
        If array keys are not in config.categories (will be auto-colored).

    Examples
    --------
    >>> arrays = {
    ...     "all_data":   durations_all,
    ...     "Hospital_A": durations_a,
    ...     "Hospital_B": durations_b,
    ... }
    >>> config  = ArraysViolinConfig.build_from_yaml("violin.yaml")
    >>> plotter = ArraysViolinPlotter(arrays, config)
    >>> plotter.plot("output.png")
    """

    def __init__(
        self,
        arrays: dict,
        config: ArraysViolinConfig | None = None,
    ) -> None:

        # ── Config ────────────────────────────────────────────────────
        if config is None:
            config = ArraysViolinConfig()
        if not isinstance(config, ArraysViolinConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an ArraysViolinConfig, "
                f"got {type(config).__name__}"
            )

        # ── arrays must be a non-empty dict ───────────────────────────
        if not isinstance(arrays, dict):
            raise TypeError(
                f"{_ERROR_PREFIX}: arrays must be a dict, "
                f"got {type(arrays).__name__}"
            )
        if not arrays:
            raise ValueError(f"{_ERROR_PREFIX}: arrays must not be empty")

        # ── Validate and clean each array ─────────────────────────────
        clean: dict[str, np.ndarray] = {}
        for key, raw in arrays.items():

            # Key must be a non-empty string
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    f"{_ERROR_PREFIX}: all keys must be non-empty strings, "
                    f"got {key!r}"
                )

            # Must be convertible to a numpy array
            try:
                arr = np.asarray(raw)
            except Exception as e:
                raise ValueError(
                    f"{_ERROR_PREFIX}: arrays[{key!r}] could not be converted "
                    f"to a numpy array: {e}"
                ) from e

            # Must be 1-D
            if arr.ndim != 1:
                raise ValueError(
                    f"{_ERROR_PREFIX}: arrays[{key!r}] must be 1-D, "
                    f"got shape {arr.shape}"
                )

            # Must be numeric
            try:
                arr = arr.astype(float)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"{_ERROR_PREFIX}: arrays[{key!r}] must contain numeric "
                    f"values, got dtype {arr.dtype}: {e}"
                ) from e

            # Drop NaN and inf, warn if significant data lost
            n_before  = len(arr)
            arr       = arr[np.isfinite(arr)]
            n_dropped = n_before - len(arr)
            if n_before > 0 and n_dropped / n_before > _NAN_WARN_THRESHOLD:
                warnings.warn(
                    f"{_WARN_PREFIX}: arrays[{key!r}] had {n_dropped} of "
                    f"{n_before} values dropped (NaN/inf) — "
                    f"{n_dropped / n_before:.0%} of data lost.",
                    UserWarning, stacklevel=2,
                )

            # Must have at least 2 finite values to draw a violin
            if len(arr) < 2:
                raise ValueError(
                    f"{_ERROR_PREFIX}: arrays[{key!r}] has fewer than 2 finite "
                    f"values after dropping NaN/inf ({len(arr)} remaining). "
                    f"Cannot draw a violin."
                )

            # Warn if all values are identical — violin degenerates to a line
            if np.all(arr == arr[0]):
                warnings.warn(
                    f"{_WARN_PREFIX}: arrays[{key!r}] contains only one unique "
                    f"value ({arr[0]}). The violin will degenerate to a line.",
                    UserWarning, stacklevel=2,
                )

            clean[key] = arr

        # ── Cross-check config keys vs array keys ─────────────────────
        config_keys = set(config.plot_order)
        array_keys  = set(clean.keys())

        missing_from_arrays = config_keys - array_keys
        if missing_from_arrays:
            warnings.warn(
                f"{_WARN_PREFIX}: the following keys are in config.categories "
                f"but not in arrays — they will be skipped: "
                f"{sorted(missing_from_arrays)}",
                UserWarning, stacklevel=2,
            )

        unconfigured = array_keys - config_keys
        if unconfigured:
            warnings.warn(
                f"{_WARN_PREFIX}: the following array keys have no entry in "
                f"config.categories — they will be auto-colored: "
                f"{sorted(unconfigured)}",
                UserWarning, stacklevel=2,
            )

        self._arrays = clean
        self._config = config

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
            Parent directory must exist.
        """
        from eventus.visualizers.plotters.arrays_violin_plotter_utils import (
            apply_y_bounds,
            build_tick_labels,
            compute_widths,
            draw_box,
            draw_percentile_lines,
            draw_points,
            draw_violin_body,
        )

        self._validate_path(path)

        cfg    = self._config
        canvas = cfg.canvas
        scfg   = cfg.style
        pcfg   = cfg.percentiles
        lcfg   = cfg.labels
        axcfg  = cfg.axes

        # ── Plot order ────────────────────────────────────────────────
        # Config order first, then any extra keys not in config
        configured = [k for k in cfg.plot_order if k in self._arrays]
        extras     = [k for k in self._arrays   if k not in cfg.plot_order]
        plot_order = configured + extras

        if not plot_order:
            raise ValueError(
                f"{_ERROR_PREFIX}: no arrays remain to plot after matching "
                f"against config.plot_order."
            )

        # ── Resolve colors / labels, compute sizes and widths ─────────
        resolved = cfg.resolve(plot_order)
        sizes    = {k: len(self._arrays[k]) for k in plot_order}
        widths   = compute_widths(self._arrays, plot_order)

        # ── Figure ────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=canvas.figsize)

        for i, key in enumerate(plot_order):
            arr   = self._arrays[key]
            color = resolved[key].color
            width = widths[key]

            draw_violin_body(ax, arr, i, width, color, scfg.bandwidth)

            if scfg.show_box:
                draw_box(ax, arr, i, color)

            if scfg.show_points:
                draw_points(ax, arr, i, width, color, scfg.point_alpha, scfg.point_size)

            if pcfg.show:
                draw_percentile_lines(ax, arr, i, width, pcfg, canvas.font_size)

        # ── Y bounds, ticks, labels ───────────────────────────────────
        apply_y_bounds(ax, axcfg)

        tick_labels = build_tick_labels(plot_order, resolved, sizes)
        ax.set_xticks(range(len(plot_order)))
        ax.set_xticklabels(tick_labels, fontsize=canvas.font_size - 1)
        ax.set_xlim(-0.5, len(plot_order) - 0.5)

        if lcfg.title:
            ax.set_title(lcfg.title, fontsize=canvas.font_size + 1)
        if lcfg.ylabel:
            ax.set_ylabel(lcfg.ylabel, fontsize=canvas.font_size)
        elif lcfg.units:
            ax.set_ylabel(lcfg.units, fontsize=canvas.font_size)
        if lcfg.xlabel:
            ax.set_xlabel(lcfg.xlabel, fontsize=canvas.font_size)

        ax.tick_params(axis="y", labelsize=canvas.font_size - 1)

        # ── Save ──────────────────────────────────────────────────────
        fig.tight_layout()
        fig.savefig(path, dpi=canvas.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _validate_path(self, path: str) -> None:
        p = pathlib.Path(path)
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{p.suffix}'. "
                f"Use .png, .jpg, or .jpeg"
            )
        if not p.parent.exists():
            raise ValueError(
                f"{_ERROR_PREFIX}: output directory does not exist: "
                f"'{p.parent}'. Create it before calling plot()."
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        sizes = {k: len(v) for k, v in self._arrays.items()}
        return (
            f"ArraysViolinPlotter(\n"
            f"  arrays  : {list(sizes.keys())}\n"
            f"  sizes   : {sizes}\n"
            f"  order   : {self._config.plot_order}\n"
            f")"
        )
