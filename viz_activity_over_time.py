"""
viz_activity_over_time.py
ActivityOverTimePlotter — plots percentage of active entities over time
with optional entered/exited arrows on a separate subplot.
"""
from __future__ import annotations
import pathlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import yaml

_ERROR_PREFIX = "[ActivityOverTimePlotter] Error"

_REQUIRED_CONFIG_KEYS  = {"general", "line", "arrows", "layout"}
_REQUIRED_GENERAL_KEYS = {"figsize", "dpi", "font_size", "title_font_size", "style", "xtick_interval"}
_REQUIRED_LINE_KEYS    = {"color", "linewidth", "fill_alpha"}
_REQUIRED_ARROW_KEYS   = {"show", "arrow_axis_y", "entered_color", "exited_color",
                           "max_size", "min_size"}
_REQUIRED_LAYOUT_KEYS  = {"top_height_ratio", "bottom_height_ratio"}

_REQUIRED_COLS = {"day", "n_total", "n_active", "pct_active", "n_entered", "n_exited"}


class ActivityOverTimePlotter:
    """
    Plots percentage of active entities over time.

    Two subplots sharing the x-axis:
    - Top panel  : line chart of pct_active (0–1 fraction)
    - Bottom panel: up/down arrows on a configurable horizontal line
                    showing entities entered (green) and exited (red)

    Pure renderer — accepts the DataFrame output of
    PipeDelimitedIntermediateEventAnalysis.activity_over_time() directly.

    Parameters
    ----------
    config_path : str
        Path to an activity_over_time_config.yaml file.
    timeseries : pd.DataFrame
        Output of activity_over_time(). Must have columns:
        [date, n_total, n_active, pct_active, n_entered, n_exited]
    """

    def __init__(self, config_path: str, timeseries: pd.DataFrame) -> None:
        self._cfg = self._load_config(config_path)
        self._validate_timeseries(timeseries)
        self._ts = timeseries.copy()
        # day column is already integer offsets — no parsing needed

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """
        Render and save the chart.

        Parameters
        ----------
        path : str
            Output file path. Supports .png, .jpg, .jpeg.
        """
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported extension '{ext}'. "
                "Use .png, .jpg, or .jpeg"
            )
        fig = self._render()
        fig.savefig(path, dpi=self._cfg["general"]["dpi"], bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Internal rendering
    # ------------------------------------------------------------------ #

    def _render(self) -> plt.Figure:
        cfg      = self._cfg
        gcfg     = cfg["general"]
        lcfg     = cfg["line"]
        acfg     = cfg["arrows"]
        laycfg   = cfg["layout"]
        fs       = gcfg["font_size"]
        title_fs = gcfg["title_font_size"]

        try:
            plt.style.use(gcfg["style"])
        except Exception:
            pass

        show_arrows = acfg["show"]

        # --- Figure and subplots ---
        height_ratios = [laycfg["top_height_ratio"], laycfg["bottom_height_ratio"]] \
                        if show_arrows else [1]
        n_rows = 2 if show_arrows else 1

        fig, axes = plt.subplots(
            n_rows, 1,
            figsize=gcfg["figsize"],
            sharex=True,
            gridspec_kw={"height_ratios": height_ratios} if show_arrows else {},
        )
        ax_line  = axes[0] if show_arrows else axes
        ax_arrow = axes[1] if show_arrows else None

        dates    = self._ts["day"]
        pct      = self._ts["pct_active"]

        # --- Top panel: line chart ---
        ax_line.plot(dates, pct, color=lcfg["color"],
                     linewidth=lcfg["linewidth"], zorder=3)

        if lcfg["fill_alpha"] > 0:
            ax_line.fill_between(dates, pct, alpha=lcfg["fill_alpha"],
                                 color=lcfg["color"], zorder=2)

        ax_line.set_ylim(0, 1.05)
        ax_line.set_ylabel("Fraction active", fontsize=fs)
        ax_line.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:.0f}" if x == int(x) else f"{x:.2f}")
        )
        ax_line.tick_params(axis="both", labelsize=fs - 1)

        # X ticks at regular intervals
        xtick_interval = gcfg.get("xtick_interval", 60)
        max_day = int(self._ts["day"].max())
        ax_line.set_xticks(range(0, max_day + 1, xtick_interval))

        title = gcfg.get("title") or "Activity over time"
        ax_line.set_title(title, fontsize=title_fs)

        # --- Bottom panel: arrows ---
        if show_arrows and ax_arrow is not None:
            self._render_arrows(ax_arrow, acfg, fs)

        fig.tight_layout()
        return fig

    def _render_arrows(self, ax, acfg: dict, fs: int) -> None:
        """Render entered/exited arrows on the bottom subplot."""
        axis_y    = acfg["arrow_axis_y"]
        max_size  = acfg["max_size"]
        min_size  = acfg["min_size"]

        # Horizontal reference line
        ax.axhline(y=axis_y, color="#AAAAAA", linewidth=0.8, zorder=1)

        # Only rows where entered/exited are not NA
        valid = self._ts.dropna(subset=["n_entered", "n_exited"])
        if valid.empty:
            ax.set_yticks([])
            return

        entered = valid["n_entered"].astype(float)
        exited  = valid["n_exited"].astype(float)

        # Scale sizes proportionally between min and max
        max_val = max(entered.max(), exited.max(), 1)

        def scale_size(series: pd.Series) -> pd.Series:
            return min_size + (series / max_val) * (max_size - min_size)

        entered_sizes = scale_size(entered)
        exited_sizes  = scale_size(exited)

        # Draw entered — up arrows above axis_y
        mask_e = entered > 0
        if mask_e.any():
            ax.scatter(
                valid.loc[mask_e, "day"],
                [axis_y + 0.15] * mask_e.sum(),
                s=entered_sizes[mask_e],
                marker="^",
                color=acfg["entered_color"],
                zorder=3,
                label="Entered",
            )

        # Draw exited — down arrows below axis_y
        mask_x = exited > 0
        if mask_x.any():
            ax.scatter(
                valid.loc[mask_x, "day"],
                [axis_y - 0.15] * mask_x.sum(),
                s=exited_sizes[mask_x],
                marker="v",
                color=acfg["exited_color"],
                zorder=3,
                label="Exited",
            )

        ax.set_ylim(0, 1)
        ax.set_yticks([axis_y])
        ax.set_yticklabels([""])
        ax.tick_params(axis="x", labelsize=fs - 1)
        ax.set_xlabel("Days from span start", fontsize=fs)

        # Legend
        legend_elements = []
        if mask_e.any():
            legend_elements.append(
                mpatches.Patch(facecolor=acfg["entered_color"], label="Entered active")
            )
        if mask_x.any():
            legend_elements.append(
                mpatches.Patch(facecolor=acfg["exited_color"], label="Exited active")
            )
        if legend_elements:
            ax.legend(handles=legend_elements, loc="upper right",
                      fontsize=fs - 1, frameon=False)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate_timeseries(self, ts: pd.DataFrame) -> None:
        if not isinstance(ts, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: timeseries must be a DataFrame, "
                f"got {type(ts).__name__}"
            )
        missing = _REQUIRED_COLS - set(ts.columns)
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: timeseries missing columns: {sorted(missing)}"
            )
        if ts.empty:
            raise ValueError(f"{_ERROR_PREFIX}: timeseries is empty")

    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError(f"{_ERROR_PREFIX}: config must be a YAML mapping")

        for section, required in [
            ("general", _REQUIRED_GENERAL_KEYS),
            ("line",    _REQUIRED_LINE_KEYS),
            ("arrows",  _REQUIRED_ARROW_KEYS),
            ("layout",  _REQUIRED_LAYOUT_KEYS),
        ]:
            if section not in cfg:
                raise ValueError(f"{_ERROR_PREFIX}: config missing section '{section}'")
            missing = required - set(cfg[section].keys())
            if missing:
                raise ValueError(
                    f"{_ERROR_PREFIX}: config '{section}' missing keys: {sorted(missing)}"
                )
        return cfg
