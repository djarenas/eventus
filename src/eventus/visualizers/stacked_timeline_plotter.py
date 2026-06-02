"""
stacked_timeline_plotter.py
StackedTimelinePlotter — visualize entities' timelines within their
observation period, with episode segments and event markers.

This class is pure orchestration. All computation lives in
stacked_timeline_plotter_utils.py.
"""
from __future__ import annotations
import warnings
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from collections import defaultdict

from eventus.visualizers.configs.stacked_timeline_config import StackedTimelineConfig
from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.cohort_timeline_utils import OBS_START_COL, OBS_END_COL
from eventus.visualizers.plot_utils import validate_path, save_figure

_ERROR_PREFIX = "[StackedTimelinePlotter] Error"

_MARKER_MAP = {
    "circle":   "o",
    "triangle": "^",
    "square":   "s",
    "diamond":  "D",
    "star":     "*",
}


class StackedTimelinePlotter:
    """
    Visualize entities' timelines within their observation period.

    One horizontal bar per entity. The bar spans their observation period.
    Episode segments and event markers are overlaid from a CohortTimeline.

    Parameters
    ----------
    cohort_timeline : CohortTimeline
        Must contain obs_start and obs_end columns.
    config : StackedTimelineConfig | None
        Plot configuration. Uses StackedTimelineConfig() defaults
        if not provided.
    sort_identity : str | None
        Episode identity to sort by — must be present in
        cohort_timeline.episode_identities and must have coverage
        columns (produced by enrich_with_episode_coverage()).
        Default None — entities appear in cohort_timeline order.
    sort_metrics : list[EpisodeCoverageMetric] | None
        Which coverage metrics to sort by, in priority order.
        Default [EpisodeCoverageMetric.ACTIVE_DAYS] when sort_identity
        is provided. Each metric corresponds to an
        eps_comp_{identity}_{metric} column. Raises if the column is
        not present in the CohortTimeline.
    ascending : bool | list[bool]
        Sort direction per metric. A single bool applies to all metrics.
        Default True.
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _cohort_timeline: CohortTimeline       # sorted/validated timeline
    _config:          StackedTimelineConfig # plot configuration

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        config:         StackedTimelineConfig | None    = None,
        sort_identity:  str | None                     = None,
        sort_metrics:   list | None                    = None,
        ascending:      bool | list[bool]              = True,
    ) -> None:
        if not isinstance(cohort_timeline, CohortTimeline):
            raise TypeError(
                f"{_ERROR_PREFIX}: cohort_timeline must be a CohortTimeline "
                f"object, got {type(cohort_timeline).__name__}"
            )
        if not cohort_timeline.has_obs_period:
            raise ValueError(
                f"{_ERROR_PREFIX}: cohort_timeline must contain an observation "
                f"period. '{OBS_START_COL}' and '{OBS_END_COL}' columns are required."
            )
        if config is None:
            config = StackedTimelineConfig()
        if not isinstance(config, StackedTimelineConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a StackedTimelineConfig "
                f"object, got {type(config).__name__}"
            )

        if sort_identity is not None:
            from eventus.types import EpisodeCoverageMetric
            self._validate_sort_args(
                sort_identity, sort_metrics, ascending, cohort_timeline
            )
            # Apply default metric if not specified
            if sort_metrics is None:
                sort_metrics = [EpisodeCoverageMetric.ACTIVE_DAYS]

            # Resolve all metrics to EpisodeCoverageMetric for consistent .value access
            resolved_metrics = [EpisodeCoverageMetric(m) for m in sort_metrics]
            date_metrics     = {EpisodeCoverageMetric.FIRST_START, EpisodeCoverageMetric.LAST_END}

            sort_cols = [
                f"eps_comp_{sort_identity}_{m.value}" for m in resolved_metrics
            ]
            sorted_data = cohort_timeline.data.copy()
            # Parse date columns for correct date-aware sorting
            for col, metric in zip(sort_cols, resolved_metrics):
                if metric in date_metrics:
                    sorted_data[col] = pd.to_datetime(sorted_data[col], errors="coerce")
                else:
                    sorted_data[col] = pd.to_numeric(sorted_data[col], errors="coerce")

            sorted_data = sorted_data.sort_values(
                by=sort_cols, ascending=ascending, na_position="last"
            )
            sorted_data = sorted_data.reset_index(drop=True)
            cohort_timeline = CohortTimeline(sorted_data, cohort_timeline.entity_col)

        self._cohort_timeline = cohort_timeline
        self._config          = config

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_sort_args(
        sort_identity: str,
        sort_metrics:  list | None,
        ascending:     bool | list[bool],
        cohort_timeline: CohortTimeline,
    ) -> None:
        from eventus.types import EpisodeCoverageMetric

        # Validate identity
        if not isinstance(sort_identity, str) or not sort_identity.strip():
            raise TypeError(
                f"{_ERROR_PREFIX}: sort_identity must be a non-empty string, "
                f"got {sort_identity!r}"
            )
        if sort_identity not in cohort_timeline.episode_identities:
            raise ValueError(
                f"{_ERROR_PREFIX}: sort_identity '{sort_identity}' not found "
                f"in cohort_timeline.episode_identities: "
                f"{cohort_timeline.episode_identities}. "
                f"Ensure the identity is present and coverage columns have "
                f"been computed via enrich_with_episode_coverage()."
            )

        # Validate metrics
        valid_metrics = set(EpisodeCoverageMetric)
        if sort_metrics is not None:
            if not isinstance(sort_metrics, list) or not sort_metrics:
                raise TypeError(
                    f"{_ERROR_PREFIX}: sort_metrics must be a non-empty list "
                    f"of EpisodeCoverageMetric values, "
                    f"got {type(sort_metrics).__name__}"
                )
            for m in sort_metrics:
                try:
                    resolved = EpisodeCoverageMetric(m)
                except ValueError:
                    raise ValueError(
                        f"{_ERROR_PREFIX}: '{m}' is not a valid "
                        f"EpisodeCoverageMetric. "
                        f"Valid values: {[e.value for e in EpisodeCoverageMetric]}"
                    )
                col = f"eps_comp_{sort_identity}_{resolved.value}"
                if col not in cohort_timeline.data.columns:
                    raise ValueError(
                        f"{_ERROR_PREFIX}: coverage column '{col}' not found "
                        f"in cohort_timeline. "
                        f"Call enrich_with_episode_coverage() on the "
                        f"CohortTimeline before sorting by coverage metrics."
                    )

        # Validate ascending
        effective_n = len(sort_metrics) if sort_metrics else 1
        if isinstance(ascending, list):
            if not all(isinstance(a, bool) for a in ascending):
                bad = [a for a in ascending if not isinstance(a, bool)]
                raise TypeError(
                    f"{_ERROR_PREFIX}: all ascending entries must be bools, "
                    f"got: {bad}"
                )
            if len(ascending) != effective_n:
                raise ValueError(
                    f"{_ERROR_PREFIX}: ascending list length ({len(ascending)}) "
                    f"must match sort_metrics length ({effective_n})"
                )
        elif not isinstance(ascending, bool):
            raise TypeError(
                f"{_ERROR_PREFIX}: ascending must be a bool or list of bools, "
                f"got {type(ascending).__name__}"
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """Save the stacked timeline plot to a file (.png, .jpg, .jpeg)."""
        from .stacked_timeline_plotter_utils import (
            resolve_x_mode, build_obs_lookup,
            precompute, format_xaxis, compute_figsize,
        )

        validate_path(path, _ERROR_PREFIX)

        cfg  = self._config
        ec   = self._cohort_timeline.entity_col
        data = self._cohort_timeline.data.copy()
        n    = len(data)

        if n > cfg.layout.max_entities:
            warnings.warn(
                f"{_ERROR_PREFIX}: {n} entities exceed "
                f"max_entities={cfg.layout.max_entities}. "
                f"Plot may be unreadable. Consider filtering.",
                UserWarning, stacklevel=2,
            )

        # ── Parse obs period dates ────────────────────────────────────
        data[OBS_START_COL] = pd.to_datetime(data[OBS_START_COL]).dt.normalize()
        data[OBS_END_COL]   = pd.to_datetime(data[OBS_END_COL]).dt.normalize()

        # ── Build lookups ─────────────────────────────────────────────
        obs_lookup = build_obs_lookup(data, ec)
        entities   = list(obs_lookup.keys())
        max_days   = max(d for _, _, d in obs_lookup.values())

        # ── Resolve layer configs ─────────────────────────────────────
        ev_cfg  = self._resolve_episode_config()
        evt_map = self._resolve_evt_configs()

        # ── Resolve episode identity for column lookup ──────────────────
        episode_identity = None
        if ev_cfg is not None:
            episode_identity = ev_cfg.identity

        # ── Precompute segments and markers ───────────────────────────
        bar_h = cfg.layout.bar_height_ratio
        color_segments, marker_groups = precompute(
            entities       = entities,
            data           = data,
            entity_col     = ec,
            obs_lookup     = obs_lookup,
            episode_identity = episode_identity,
            ev_color       = ev_cfg.color if ev_cfg else cfg.poi.color_no_episodes,
            evt_cfg_map    = evt_map,
            poi            = cfg.poi,
            bar_h          = bar_h,
            jitter         = cfg.layout.jitter,
            jitter_ratio   = cfg.layout.jitter_ratio,
        )

        # ── Figure ────────────────────────────────────────────────────
        try:
            plt.style.use(cfg.layout.style)
        except Exception:
            pass

        fig, ax = plt.subplots(
            figsize=compute_figsize(n, cfg.layout.row_height, cfg.canvas.figsize)
        )

        # ── Draw segments — one broken_barh call per color ────────────
        for color, segs in color_segments.items():
            by_y: dict[int, list] = defaultdict(list)
            for left, width, y in segs:
                by_y[y].append((left, width))
            poi_colors = {
                cfg.poi.color_before,
                cfg.poi.color_middle,
                cfg.poi.color_after,
                cfg.poi.color_no_episodes,
            }
            for y, xranges in by_y.items():
                ax.broken_barh(
                    xranges,
                    (y - bar_h / 2, bar_h),
                    facecolors = color,
                    zorder     = 1 if color in poi_colors else 2,
                )

        # ── Draw event markers ───────────────────────────────────
        for (color, marker, size, alpha), points in marker_groups.items():
            if not points:
                continue
            xs, ymins, ymaxs = zip(*points)
            mk = _MARKER_MAP.get(marker, "o")
            if marker == "line":
                ax.vlines(
                    x          = xs,
                    ymin       = ymins,
                    ymax       = ymaxs,
                    colors     = color,
                    linewidths = size / 10,
                    zorder     = 5,
                )
            else:
                y_centers = [(mn + mx) / 2 for mn, mx in zip(ymins, ymaxs)]
                ax.scatter(
                    xs, y_centers,
                    s          = size ** 2,
                    color      = color,
                    marker     = mk,
                    alpha      = alpha,
                    zorder     = 5,
                    linewidths = 0,
                )

        # ── Axes ──────────────────────────────────────────────────────
        ax.set_yticks(range(n))
        if cfg.layout.show_entity_labels:
            ax.set_yticklabels(entities, fontsize=cfg.canvas.font_size - 2)
        else:
            ax.set_yticklabels([])
            ax.tick_params(axis="y", left=False)
        ax.set_ylim(-0.5, n - 0.5)
        ax.invert_yaxis()
        ax.set_xlim(0, max_days)

        # ── X axis ────────────────────────────────────────────────────
        x_mode        = resolve_x_mode(data, cfg.x_axis.mode)
        obs_start_ref = (
            data[OBS_START_COL].iloc[0] if x_mode == "calendar" else None
        )

        format_xaxis(
            ax             = ax,
            x_mode         = x_mode,
            max_days       = max_days,
            span_start_ref = obs_start_ref,
            font_size      = cfg.canvas.font_size,
            x_cfg          = cfg.x_axis
        )

        ax.tick_params(axis="x", labelsize=cfg.x_axis.tick_font_size)  
        ax.tick_params(axis="y", left=False, labelleft=False)  

        # ── Title and legend ──────────────────────────────────────────
        ax.set_title(
            cfg.labels.title or f"Timeline — {ec}", fontsize=cfg.labels.title_font_size
        )

        if cfg.legend.show:
            legend_kwargs = dict(
                handles  = self._build_legend_handles(ev_cfg, evt_map),
                fontsize = cfg.legend.font_size,
                frameon  = True,
            )
            if cfg.legend.outside:
                legend_kwargs["loc"]            = "upper left"
                legend_kwargs["bbox_to_anchor"] = (1.01, 1)
                legend_kwargs["borderaxespad"]  = 0
            else:
                legend_kwargs["loc"] = cfg.legend.location
            ax.legend(**legend_kwargs)

        fig.tight_layout()
        save_figure(fig, path, cfg.canvas.dpi)

    # ------------------------------------------------------------------ #
    # Config resolution helpers
    # ------------------------------------------------------------------ #

    def _resolve_episode_config(self):
        """Return the first EpisodeLayerConfig from config, or None."""
        if not self._cohort_timeline.episode_identities:
            return None
        if not self._config.episodes:
            warnings.warn(
                "[StackedTimelinePlotter] cohort_timeline has episode columns "
                "but no episodes entry found in config. "
                "Only the observation period bar will be drawn. "
                "Add an episodes entry to show episode segments.",
                UserWarning, stacklevel=3,
            )
            return None
        return self._config.episodes[0]

    def _resolve_evt_configs(self):
        """Return {col: EventLayerConfig} for configured identities."""
        evt_map = {}
        for ocfg in self._config.events:
            col = f"evt_{ocfg.identity}"
            if col not in self._cohort_timeline.data.columns:
                warnings.warn(
                    f"[StackedTimelinePlotter] events has "
                    f"identity '{ocfg.identity}' but column '{col}' was "
                    f"not found in cohort_timeline — skipping.",
                    UserWarning, stacklevel=3,
                )
                continue
            evt_map[col] = ocfg
        return evt_map

    def _build_legend_handles(self, ev_cfg, evt_cfg_map) -> list:
        """Build legend handle list from resolved layer configs."""
        cfg     = self._config
        poi     = cfg.poi
        handles = []

        if cfg.legend.show_poi_in_legend:
            handles.append(mpatches.Patch(
                facecolor=poi.color_no_episodes, label="No episodes"
            ))
        handles.append(mpatches.Patch(
            facecolor=poi.color_before, label="Inactive before"
        ))
        if ev_cfg is not None:
            handles.append(mpatches.Patch(
                facecolor = ev_cfg.color,
                alpha     = ev_cfg.alpha,
                label     = ev_cfg.label or ev_cfg.identity,
            ))
        handles.append(mpatches.Patch(
            facecolor=poi.color_middle, label="Inactive gap"
        ))
        handles.append(mpatches.Patch(
            facecolor=poi.color_after, label="Inactive after"
        ))
        for col, ocfg in evt_cfg_map.items():
            handles.append(Line2D(
                [0], [0],
                marker          = _MARKER_MAP.get(ocfg.marker, "o"),
                color           = "none",
                markerfacecolor = ocfg.color,
                markersize      = ocfg.size,
                label           = ocfg.label or ocfg.identity,
            ))
        return handles

    # ------------------------------------------------------------------ #
    # Validation and dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"StackedTimelinePlotter(\n"
            f"  entities             : {len(self._cohort_timeline):,}\n"
            f"  episode_identities     : {self._cohort_timeline.episode_identities}\n"
            f"  event_identities: {self._cohort_timeline.event_identities}\n"
            f"  x_axis               : '{self._config.x_axis.mode}'\n"
            f")"
        )
