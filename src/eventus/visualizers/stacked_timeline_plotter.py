"""
stacked_timeline_plotter.py
StackedTimelinePlotter — visualize entities' timelines within their
observation period, with event segments and occurrence markers.

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

# Valid sort columns — identity-independent ones only.
# Identity-prefixed columns (evt_{identity}_active_days etc.) are
# accepted dynamically in _validate_sort_args.
_SORT_DATE = {
    "obs_start",
    "obs_end",
}
_SORT_NUMERIC_STATIC = {
    "obs_duration_days",
}


class StackedTimelinePlotter:
    """
    Visualize entities' timelines within their observation period.

    One horizontal bar per entity. The bar spans their observation period.
    Event segments and occurrence markers are overlaid from a CohortTimeline.

    Parameters
    ----------
    cohort_timeline : CohortTimeline
        Must contain obs_start and obs_end columns.
    config : StackedTimelineConfig | None
        Plot configuration. Uses StackedTimelineConfig.build_with_defaults()
        if not provided.
    sort_by : list[str] | None
        Column names to sort entities by before plotting. Must exist in
        cohort_timeline.data. Common values:
        'obs_duration_days', 'obs_start', 'obs_end',
        or identity-prefixed columns like
        'evt_inpatient_hospitalization_active_days'.
        Default None — entities appear in cohort_timeline order.
    ascending : bool | list[bool]
        Sort direction. Default True.
    """

    def __init__(
        self,
        cohort_timeline: CohortTimeline,
        config:    StackedTimelineConfig | None = None,
        sort_by:   list[str] | None            = None,
        ascending: bool | list[bool]           = True,
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
            config = StackedTimelineConfig.build_with_defaults()
        if not isinstance(config, StackedTimelineConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a StackedTimelineConfig "
                f"object, got {type(config).__name__}"
            )

        if sort_by is not None:
            self._validate_sort_args(sort_by, ascending, cohort_timeline.data)
            sorted_data, temp_cols = self._prepare_for_sort(cohort_timeline.data, sort_by)

            # Replace any pipe-delimited sort columns with their temp proxies
            actual_sort_by = list(sort_by)
            for orig_col, temp_col in temp_cols:
                idx = actual_sort_by.index(orig_col)
                actual_sort_by[idx] = temp_col

            sorted_data = sorted_data.sort_values(
                by=actual_sort_by, ascending=ascending, na_position="last"
            )
            # Drop temp sort columns before constructing CohortTimeline
            drop_cols = [temp for _, temp in temp_cols]
            sorted_data = sorted_data.drop(columns=drop_cols, errors="ignore")
            sorted_data = sorted_data.reset_index(drop=True)
            cohort_timeline = CohortTimeline(sorted_data, cohort_timeline.entity_col)

        self._cohort_timeline = cohort_timeline
        self._config          = config

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_sort_args(
        sort_by:   list[str],
        ascending: bool | list[bool],
        data:      pd.DataFrame,
    ) -> None:
        if not isinstance(sort_by, list) or not sort_by:
            raise TypeError(
                f"{_ERROR_PREFIX}: sort_by must be a non-empty list of "
                f"column name strings, got {type(sort_by).__name__}"
            )
        if not all(isinstance(s, str) for s in sort_by):
            bad = [s for s in sort_by if not isinstance(s, str)]
            raise TypeError(
                f"{_ERROR_PREFIX}: all sort_by entries must be strings, "
                f"got non-string values: {bad}"
            )
        # Any column that exists in the data is valid
        missing = [c for c in sort_by if c not in data.columns]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: sort_by column(s) not found in "
                f"cohort_timeline.data: {missing}. "
                f"Available columns: {sorted(data.columns.tolist())}"
            )
        if isinstance(ascending, list):
            if not all(isinstance(a, bool) for a in ascending):
                bad = [a for a in ascending if not isinstance(a, bool)]
                raise TypeError(
                    f"{_ERROR_PREFIX}: all ascending entries must be bools, "
                    f"got: {bad}"
                )
            if len(ascending) != len(sort_by):
                raise ValueError(
                    f"{_ERROR_PREFIX}: ascending list length ({len(ascending)}) "
                    f"must match sort_by length ({len(sort_by)})"
                )
        elif not isinstance(ascending, bool):
            raise TypeError(
                f"{_ERROR_PREFIX}: ascending must be a bool or list of bools, "
                f"got {type(ascending).__name__}"
            )

    @staticmethod
    def _prepare_for_sort(
        data:    pd.DataFrame,
        sort_by: list[str],
    ) -> pd.DataFrame:
        """
        Cast sort columns to correct types before sorting, without
        destroying original column data.

        Date columns (obs_start, obs_end) are parsed as datetime in-place.
        Event starts/ends (pipe-delimited) are sorted by extracting the
        first date into a temporary _sort_{col} column, which is dropped
        after sorting. Numeric columns are cast to float.
        """
        data = data.copy()
        temp_cols = []

        for col in sort_by:
            if col in _SORT_DATE:
                data[col] = pd.to_datetime(data[col], errors="coerce")
            elif (col.startswith("evt_") and
                  (col.endswith("_starts") or col.endswith("_ends"))):
                # Pipe-delimited date strings — extract first date for sorting
                # into a temp column, leave original intact
                temp = f"_sort_tmp_{col}"
                data[temp] = data[col].apply(
                    lambda v: pd.to_datetime(
                        str(v).split(" | ")[0].strip(), errors="coerce"
                    ) if pd.notna(v) else pd.NaT
                )
                temp_cols.append((col, temp))
            else:
                # Numeric — computed stats, obs_duration_days, etc.
                data[col] = pd.to_numeric(data[col], errors="coerce").astype(float)

        return data, temp_cols

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
        ev_cfg  = self._resolve_event_config()
        occ_map = self._resolve_occ_configs()

        # ── Resolve event identity for column lookup ──────────────────
        event_identity = None
        if ev_cfg is not None:
            event_identity = ev_cfg.identity

        # ── Precompute segments and markers ───────────────────────────
        bar_h = cfg.layout.bar_height_ratio
        color_segments, marker_groups = precompute(
            entities       = entities,
            data           = data,
            entity_col     = ec,
            obs_lookup     = obs_lookup,
            event_identity = event_identity,
            ev_color       = ev_cfg.color if ev_cfg else cfg.poi.color_no_events,
            occ_cfg_map    = occ_map,
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
                cfg.poi.color_no_events,
            }
            for y, xranges in by_y.items():
                ax.broken_barh(
                    xranges,
                    (y - bar_h / 2, bar_h),
                    facecolors = color,
                    zorder     = 1 if color in poi_colors else 2,
                )

        # ── Draw occurrence markers ───────────────────────────────────
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
                handles  = self._build_legend_handles(ev_cfg, occ_map),
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

    def _resolve_event_config(self):
        """Return the first EventLayerConfig from config, or None."""
        if not self._cohort_timeline.event_identities:
            return None
        if not self._config.events:
            warnings.warn(
                "[StackedTimelinePlotter] cohort_timeline has event columns "
                "but no events entry found in config. "
                "Only the observation period bar will be drawn. "
                "Add an events entry to show event segments.",
                UserWarning, stacklevel=3,
            )
            return None
        return self._config.events[0]

    def _resolve_occ_configs(self):
        """Return {col: OccurrenceLayerConfig} for configured identities."""
        occ_map = {}
        for ocfg in self._config.occurrences:
            col = f"occ_{ocfg.identity}"
            if col not in self._cohort_timeline.data.columns:
                warnings.warn(
                    f"[StackedTimelinePlotter] occurrences has "
                    f"identity '{ocfg.identity}' but column '{col}' was "
                    f"not found in cohort_timeline — skipping.",
                    UserWarning, stacklevel=3,
                )
                continue
            occ_map[col] = ocfg
        return occ_map

    def _build_legend_handles(self, ev_cfg, occ_cfg_map) -> list:
        """Build legend handle list from resolved layer configs."""
        cfg     = self._config
        poi     = cfg.poi
        handles = []

        if cfg.legend.show_poi_in_legend:
            handles.append(mpatches.Patch(
                facecolor=poi.color_no_events, label="No events"
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
        for col, ocfg in occ_cfg_map.items():
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
            f"  event_identities     : {self._cohort_timeline.event_identities}\n"
            f"  occurrence_identities: {self._cohort_timeline.occurrence_identities}\n"
            f"  x_axis               : '{self._config.x_axis.mode}'\n"
            f")"
        )
