"""
plot_utils.py
Universal plotting utilities shared across all eventus visualizers.

Functions
---------
validate_path       — check output file extension and parent directory
save_figure         — save and close a matplotlib figure
apply_style         — apply font sizes and title to a figure or axes
"""
from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from eventus.visualizers.configs.base_plot_config import AxisLabels, CanvasConfig


# ── Path validation ───────────────────────────────────────────────────────────

def validate_path(path: str, error_prefix: str) -> None:
    """
    Raise if the output path has an unsupported extension or its
    parent directory does not exist.

    Parameters
    ----------
    path : str
        Output file path.
    error_prefix : str
        Prefix for error messages, e.g. "[MyPlotter] Error".
    """
    p   = pathlib.Path(path)
    ext = p.suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(
            f"{error_prefix}: unsupported file extension '{ext}'. "
            f"Use .png, .jpg, or .jpeg"
        )
    if not p.parent.exists():
        raise ValueError(
            f"{error_prefix}: output directory does not exist: "
            f"'{p.parent}'. Create it before calling plot()."
        )


# ── Save ──────────────────────────────────────────────────────────────────────

def save_figure(
    fig:     Figure,
    path:    str,
    dpi:     int,
    verbose: bool = False,
) -> None:
    """
    Save a matplotlib figure and close it.

    Parameters
    ----------
    fig     : Figure to save.
    path    : Output file path.
    dpi     : Render resolution.
    verbose : If True, print the saved path to stdout. Default False.
    """
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    if verbose:
        print(f"Saved: {path}")


# ── Style application ─────────────────────────────────────────────────────────

def apply_style(
    fig:        Figure,
    axes:       "Axes | list[Axes]",
    canvas:     CanvasConfig,
    labels:     AxisLabels,
    auto_title: str,
) -> None:
    """
    Apply font sizes and title to a figure.

    Parameters
    ----------
    fig        : The matplotlib Figure.
    axes       : Single Axes or list of Axes (for faceted plots).
    canvas     : CanvasConfig — provides font_size.
    labels     : AxisLabels — title overrides auto_title when set.
    auto_title : Fallback title when labels.title is None.
    """
    font_size   = canvas.font_size
    final_title = labels.title if labels.title is not None else auto_title

    if isinstance(axes, list):
        fig.suptitle(final_title, fontsize=font_size + 1)
        for ax in axes:
            ax.tick_params(labelsize=font_size - 1)
    else:
        axes.set_title(final_title, fontsize=font_size + 1)
        axes.tick_params(labelsize=font_size - 1)
