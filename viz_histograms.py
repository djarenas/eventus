"""
viz_histograms.py
EventAnalysisHistogramPlotter — histograms and violin plots for
PipeDelimitedIntermediateEvents.
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

_ERROR_PREFIX = "[EventAnalysisHistogramPlotter] Error"

_REQUIRED_CONFIG_KEYS    = {"general", "histogram", "violin"}
_REQUIRED_GENERAL_KEYS   = {"dpi", "font_size", "title_font_size", "style"}
_REQUIRED_HISTOGRAM_KEYS = {"bins", "color", "edgecolor", "alpha", "figsize", "legend_loc", "subtitle_loc"}
_REQUIRED_VIOLIN_KEYS    = {"color", "alpha", "inner", "figsize", "scale_by_n", "max_width"}


# --------------------------------------------------------------------------- #
# Workhorse data extractors — independently callable
# --------------------------------------------------------------------------- #

def _get_active_days(data: pd.DataFrame) -> pd.Series:
    """Active days for all entities with any coverage."""
    return data[data["active_days"].notna()]["active_days"].dropna().astype(float)


def _get_inactive_days(data: pd.DataFrame) -> pd.Series:
    """Total inactive days for all entities with any coverage."""
    return data[data["active_days"].notna()]["inactive_days"].dropna().astype(float)


def _get_inactive_before(data: pd.DataFrame) -> pd.Series:
    """Inactive days before first event — only entities where > 0."""
    covered = data[data["active_days"].notna()]
    s = covered["inactive_days_before_first_event"].dropna().astype(float)
    return s[s > 0]


def _get_inactive_after(data: pd.DataFrame) -> pd.Series:
    """Inactive days after last event — only entities where > 0."""
    covered = data[data["active_days"].notna()]
    s = covered["inactive_days_after_last_event"].dropna().astype(float)
    return s[s > 0]


def _get_inactive_middle(data: pd.DataFrame) -> pd.Series:
    """Inactive days in middle gaps — only entities where > 0."""
    covered = data[data["active_days"].notna()]
    s = covered["inactive_days_middle"].dropna().astype(float)
    return s[s > 0]


# --------------------------------------------------------------------------- #
# Internal plot helpers
# --------------------------------------------------------------------------- #

def _validate_path(path: str) -> None:
    ext = pathlib.Path(path).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(
            f"{_ERROR_PREFIX}: unsupported extension '{ext}'. "
            "Use .png, .jpg, or .jpeg"
        )


def _plot_histogram(
    series: pd.Series,
    title: str,
    xlabel: str,
    cfg: dict,
    path: str,
    n_total: int,
) -> None:
    """Render and save one histogram."""
    if len(series) == 0:
        print(f"Warning: no data for '{title}' — skipping")
        return

    hcfg = cfg["histogram"]
    gcfg = cfg["general"]
    fs   = gcfg["font_size"]

    try:
        plt.style.use(gcfg["style"])
    except Exception:
        pass

    fig, ax = plt.subplots(figsize=hcfg["figsize"])

    ax.hist(
        series,
        bins=hcfg["bins"],
        color=hcfg["color"],
        edgecolor=hcfg["edgecolor"],
        alpha=hcfg["alpha"],
    )

    # Percentile lines
    for p, ls in [(25, ":"), (50, "--"), (75, ":")]:
        val = np.percentile(series, p)
        ax.axvline(val, color="#333333", linewidth=0.9, linestyle=ls,
                   label=f"p{p}={val:.0f}d")

    ax.set_title(title, fontsize=gcfg["title_font_size"])
    ax.set_xlabel(xlabel, fontsize=fs)
    ax.set_ylabel("Count", fontsize=fs)
    ax.tick_params(labelsize=fs - 1)

    # n= subtitle
    pct = 100 * len(series) / n_total if n_total > 0 else 0.0
    subtitle = f"n={len(series):,} ({pct:.1f}% of all entities)"
    _loc_map = {
        "upper right": (0.98, 0.97, "right", "top"),
        "upper left":  (0.02, 0.97, "left",  "top"),
        "lower right": (0.98, 0.03, "right", "bottom"),
        "lower left":  (0.02, 0.03, "left",  "bottom"),
    }
    sx, sy, sha, sva = _loc_map.get(hcfg.get("subtitle_loc", "upper right"),
                                     (0.98, 0.97, "right", "top"))
    ax.text(sx, sy, subtitle, transform=ax.transAxes,
            ha=sha, va=sva, fontsize=fs - 1, color="#555555")

    ax.legend(loc=hcfg.get("legend_loc", "upper right"), fontsize=fs - 1, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=gcfg["dpi"], bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# --------------------------------------------------------------------------- #
# Main class
# --------------------------------------------------------------------------- #

class EventAnalysisHistogramPlotter:
    """
    Histograms and violin plots for PipeDelimitedIntermediateEvents.

    Each plot method produces one figure saved to a file.
    Histograms show percentile lines (p25, p50, p75).
    All plots filter to entities where the metric > 0 where appropriate.
    n and % shown relative to all entities in the intermediate.

    Parameters
    ----------
    config_path : str
        Path to histograms_config.yaml.
    intermediate : PipeDelimitedIntermediateEvents
        The analysis result to plot.
    """

    def __init__(self, config_path: str, intermediate) -> None:
        from .pipe_delimited_intermediate_events import (
            PipeDelimitedIntermediateEvents
        )
        if not isinstance(intermediate, PipeDelimitedIntermediateEvents):
            raise TypeError(
                f"{_ERROR_PREFIX}: intermediate must be a "
                f"PipeDelimitedIntermediateEvents, "
                f"got {type(intermediate).__name__}"
            )
        self._cfg          = self._load_config(config_path)
        self._intermediate = intermediate
        self._data         = intermediate.data
        self._n_total      = len(intermediate.data)

    # ------------------------------------------------------------------ #
    # Public plot methods
    # ------------------------------------------------------------------ #

    def plot_active_days(self, path: str) -> None:
        """Histogram of active days for all covered entities."""
        _validate_path(path)
        _plot_histogram(
            _get_active_days(self._data),
            "Active days", "Days", self._cfg, path, self._n_total,
        )

    def plot_inactive_days(self, path: str) -> None:
        """Histogram of total inactive days for all covered entities."""
        _validate_path(path)
        _plot_histogram(
            _get_inactive_days(self._data),
            "Total inactive days", "Days", self._cfg, path, self._n_total,
        )

    def plot_inactive_before(self, path: str) -> None:
        """Histogram of inactive days before first event (entities where > 0)."""
        _validate_path(path)
        _plot_histogram(
            _get_inactive_before(self._data),
            "Inactive days before first event", "Days",
            self._cfg, path, self._n_total,
        )

    def plot_inactive_after(self, path: str) -> None:
        """Histogram of inactive days after last event (entities where > 0)."""
        _validate_path(path)
        _plot_histogram(
            _get_inactive_after(self._data),
            "Inactive days after last event", "Days",
            self._cfg, path, self._n_total,
        )

    def plot_inactive_middle(self, path: str) -> None:
        """Histogram of inactive days in middle gaps (entities where > 0)."""
        _validate_path(path)
        _plot_histogram(
            _get_inactive_middle(self._data),
            "Inactive days (middle gaps)", "Days",
            self._cfg, path, self._n_total,
        )

    def plot_violin(self, path: str) -> None:
        """
        Violin plot comparing inactive metrics side by side.
        Shows: before first event, after last event, middle gaps, total inactive.
        Each filtered to entities where > 0. Shared y-axis for honest comparison.
        Labels show n and % of all entities.
        """
        _validate_path(path)
        vcfg = self._cfg["violin"]
        gcfg = self._cfg["general"]
        fs   = gcfg["font_size"]

        try:
            plt.style.use(gcfg["style"])
        except Exception:
            pass

        series_map = {
            "Before": _get_inactive_before(self._data),
            "After":  _get_inactive_after(self._data),
            "Middle": _get_inactive_middle(self._data),
            "Total":  _get_inactive_days(self._data),
        }

        labels    = []
        data_list = []
        for label, s in series_map.items():
            if len(s) > 0:
                pct = 100 * len(s) / self._n_total if self._n_total > 0 else 0.0
                labels.append(f"{label}\n(n={len(s):,}, {pct:.1f}%)")
                data_list.append(s.values)

        if not data_list:
            print("Warning: no data to plot in violin — skipping")
            return

        fig, ax = plt.subplots(figsize=vcfg["figsize"])

        # Compute widths scaled by n if requested
        max_w = vcfg.get("max_width", 0.8)
        if vcfg.get("scale_by_n", True):
            ns      = [len(d) for d in data_list]
            max_n   = max(ns)
            widths  = [max_w * n / max_n for n in ns]
        else:
            widths  = [max_w] * len(data_list)

        parts = ax.violinplot(
            data_list,
            positions=range(len(data_list)),
            showmedians=True,
            showextrema=True,
            widths=widths,
        )

        for pc in parts["bodies"]:
            pc.set_facecolor(vcfg["color"])
            pc.set_alpha(vcfg["alpha"])
            pc.set_edgecolor("#333333")

        for part in ["cmedians", "cmins", "cmaxes", "cbars"]:
            if part in parts:
                parts[part].set_color("#333333")
                parts[part].set_linewidth(1.0)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=fs - 1)
        ax.set_ylabel("Days", fontsize=fs)
        ax.set_title(
            "Distribution of inactive days by type",
            fontsize=gcfg["title_font_size"],
        )
        ax.tick_params(axis="y", labelsize=fs - 1)

        fig.tight_layout()

        # Subtitle outside axes — placed in figure coords to avoid overlap
        fig.text(
            0.99, 0.01,
            "Before/After/Middle: only entities where value > 0  |  Total: all covered entities",
            ha="right", va="bottom",
            fontsize=fs - 2, color="#555555",
        )
        fig.savefig(path, dpi=gcfg["dpi"], bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Config loading
    # ------------------------------------------------------------------ #

    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError(f"{_ERROR_PREFIX}: config must be a YAML mapping")
        for section, required in [
            ("general",   _REQUIRED_GENERAL_KEYS),
            ("histogram", _REQUIRED_HISTOGRAM_KEYS),
            ("violin",    _REQUIRED_VIOLIN_KEYS),
        ]:
            if section not in cfg:
                raise ValueError(f"{_ERROR_PREFIX}: config missing section '{section}'")
            missing = required - set(cfg[section].keys())
            if missing:
                raise ValueError(
                    f"{_ERROR_PREFIX}: config '{section}' missing keys: {sorted(missing)}"
                )
        return cfg
