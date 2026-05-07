"""occurrence_result_plotter_utils.py  
  
Shared drawing primitives for occurrence result plotters.  
No class state — only data and config inputs.  
"""  
from __future__ import annotations  
  
import math  
import pathlib  
import numpy as np  
import pandas as pd  
import matplotlib.pyplot as plt  
  
from matplotlib.axes import Axes  
from matplotlib.figure import Figure  
  
from eventus.visualizers.occurrences.occurrence_result_plotter_config import (  
    HistogramPlotConfig,  
    BinsConfig,  
    AutoSpec,  
    FixedWidthSpec,  
    PercentileSpec,  
    LogSpec,  
    CustomSpec,  
)  
  
# ------------------------------------------------------------------ #  
# Path validation  
# ------------------------------------------------------------------ #  
  
def validate_path(path: str, error_prefix: str) -> None:  
    ext = pathlib.Path(path).suffix.lower()  
    if ext not in {".png", ".jpg", ".jpeg"}:  
        raise ValueError(  
            f"{error_prefix} unsupported file extension '{ext}'. "  
            "Use .png, .jpg, or .jpeg"  
        )  
  
# ------------------------------------------------------------------ #  
# Style application  
# ------------------------------------------------------------------ #  
  
def apply_general_config(  
    fig: Figure,  
    axes,  
    config: HistogramPlotConfig,  
    title: str | None,  
    auto_title: str,  
) -> None:  
    style_cfg = config.style  
  
    mpl_style = getattr(style_cfg, "mpl_style", None) or getattr(style_cfg, "style", None)  
    if mpl_style:  
        try:  
            plt.style.use(mpl_style)  
        except Exception:  
            pass  
  
    font_size = getattr(style_cfg, "font_size", 11)  
    title_font_size = getattr(style_cfg, "title_font_size", font_size + 1)  
  
    final_title = title if title is not None else auto_title  
    if isinstance(axes, list):  
        fig.suptitle(final_title, fontsize=title_font_size)  
        for ax in axes:  
            ax.tick_params(labelsize=font_size - 1)  
    else:  
        axes.set_title(final_title, fontsize=title_font_size)  
        axes.tick_params(labelsize=font_size - 1)  
  
# ------------------------------------------------------------------ #  
# Bins  
# ------------------------------------------------------------------ #  
  
def compute_bins(series: pd.Series, bins_cfg: BinsConfig) -> np.ndarray:  
    clean = series.dropna().to_numpy()  
    if clean.size == 0:  
        return np.array([0.0, 1.0])  
  
    spec = bins_cfg.spec  
  
    if isinstance(spec, AutoSpec):  
        return np.histogram_bin_edges(clean, bins="auto")  
  
    if isinstance(spec, CustomSpec):  
        return np.asarray(spec.edges, dtype=float)  
  
    if isinstance(spec, FixedWidthSpec):  
        left = float(spec.min) if spec.min is not None else float(np.min(clean))  
        right = float(spec.max) if spec.max is not None else float(np.max(clean))  
        if right <= left:  
            right = left + spec.width  
  
        n = max(1, int(math.ceil((right - left) / spec.width)))  
        edges = left + np.arange(n + 1) * spec.width  
        if edges[-1] < right:  
            edges = np.append(edges, right)  
        return edges  
  
    if isinstance(spec, PercentileSpec):  
        q = np.linspace(0, 100, spec.n_bins + 1)  
        edges = np.percentile(clean, q)  
  
        # Handle constant / repeated-percentile values  
        edges = np.unique(edges)  
        if edges.size < 2:  
            c = float(clean[0])  
            return np.array([c - 0.5, c + 0.5])  
        return edges  
  
    if isinstance(spec, LogSpec):  
        # derive bounds  
        if spec.min is not None:  
            left = float(spec.min)  
        else:  
            positive = clean[clean > 0]  
            if positive.size == 0:  
                raise ValueError("Cannot use log bins: data has no positive values.")  
            left = float(np.min(positive))  
  
        if spec.max is not None:  
            right = float(spec.max)  
        else:  
            positive = clean[clean > 0]  
            if positive.size == 0:  
                raise ValueError("Cannot use log bins: data has no positive values.")  
            right = float(np.max(positive))  
  
        if right <= left:  
            right = left * 10.0  
  
        return np.logspace(np.log10(left), np.log10(right), spec.n_bins + 1)  
  
    raise TypeError(f"Unsupported bins spec: {type(spec).__name__}")  
  
# ------------------------------------------------------------------ #  
# Histogram drawing  
# ------------------------------------------------------------------ #  
  
def draw_histogram(  
    ax: Axes,  
    series: pd.Series,  
    cfg: HistogramPlotConfig,  
    label: str | None = None,  
) -> None:  
    clean = series.dropna()  
    if clean.empty:  
        ax.text(  
            0.5, 0.5, "No data",  
            transform=ax.transAxes,  
            ha="center",  
            va="center",  
            fontsize=10,  
            color="#AAAAAA",  
        )  
        return  
  
    bins = compute_bins(clean, cfg.bins)  
    style = cfg.style  
  
    ax.hist(  
        clean.to_numpy(),  
        bins=bins,  
        color=getattr(style, "color", "#4C78A8"),  
        edgecolor=getattr(style, "edgecolor", None),  
        alpha=getattr(style, "alpha", 0.85),  
        label=label,  
    )  
    ax.set_xlim(float(bins[0]), float(bins[-1]))  
  
# ------------------------------------------------------------------ #  
# Percentile lines  
# ------------------------------------------------------------------ #  
  
def draw_percentile_lines(  
    ax: Axes,  
    series: pd.Series,  
    cfg: HistogramPlotConfig,  
) -> None:  
    pct_cfg = cfg.percentile_lines  
    if not getattr(pct_cfg, "show", False):  
        return  
  
    clean = series.dropna().to_numpy()  
    if clean.size == 0:  
        return  
  
    vals = getattr(pct_cfg, "values", [])  
    linestyle = getattr(pct_cfg, "linestyle", "dashed")  
    show_labels = getattr(pct_cfg, "show_labels", True)  
  
    for p in vals:  
        x = float(np.percentile(clean, p))  
        ax.axvline(x, linestyle=linestyle, linewidth=1.2, alpha=0.9)  
        if show_labels:  
            ax.text(x, ax.get_ylim()[1], f"P{p}", rotation=90, va="top", ha="right", fontsize=8)  
  
# ------------------------------------------------------------------ #  
# Shared x-limits  
# ------------------------------------------------------------------ #  
  
def resolve_x_limits(  
    series_list: list[pd.Series],  
    bins_cfg: BinsConfig,  
) -> tuple[float, float]:  
    spec = bins_cfg.spec  
  
    if isinstance(spec, CustomSpec):  
        return float(spec.edges[0]), float(spec.edges[-1])  
  
    if isinstance(spec, (FixedWidthSpec, LogSpec)) and spec.min is not None and spec.max is not None:  
        return float(spec.min), float(spec.max)  
  
    all_vals = pd.concat([s.dropna() for s in series_list]) if series_list else pd.Series(dtype=float)  
    if all_vals.empty:  
        return 0.0, 1.0  
  
    data_min = float(all_vals.min())  
    data_max = float(all_vals.max())  
  
    if isinstance(spec, FixedWidthSpec):  
        x_min = float(spec.min) if spec.min is not None else data_min  
        x_max = float(spec.max) if spec.max is not None else data_max  
    elif isinstance(spec, LogSpec):  
        pos = all_vals[all_vals > 0]  
        if pos.empty:  
            return 0.0, 1.0  
        x_min = float(spec.min) if spec.min is not None else float(pos.min())  
        x_max = float(spec.max) if spec.max is not None else float(pos.max())  
    else:  
        x_min, x_max = data_min, data_max  
  
    if x_max <= x_min:  
        x_max = x_min + 1.0  
    return x_min, x_max  
  
# ------------------------------------------------------------------ #  
# Save  
# ------------------------------------------------------------------ #  
  
def save_figure(fig: Figure, path: str, dpi: int) -> None:  
    fig.savefig(path, dpi=dpi, bbox_inches="tight")  
    plt.close(fig)  
    print(f"Saved: {path}")  