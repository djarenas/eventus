"""
stacked_timeline_plotter.py
StackedTimelinePlotter — visualize entities' timelines within their
period of interest, with event segments and occurrence markers.

This class is pure orchestration. All computation lives in
stacked_timeline_plotter_utils.py.
"""
from __future__ import annotations
import warnings
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from collections import defaultdict

from .stacked_timeline_config import StackedTimelineConfig
from eventus.pipe_delimited_format.pipe_delimited_format import (
    PipeDelimitedFormat,
    SPAN_START_COL,
    SPAN_END_COL,
)

_ERROR_PREFIX = "[StackedTimelinePlotter] Error"

_MARKER_MAP = {
    "circle":   "o",
    "triangle": "^",
    "square":   "s",
    "diamond":  "D",
    "star":     "*",
}

# Valid sort columns and their types for correct pre-sort casting
_SORT_NUMERIC = {
    "active_days",
    "inactive_days",
    "inactive_days_before_first_event",
    "inactive_days_after_last_event",
    "inactive_days_middle",
    "span_duration_days",
}
_SORT_DATE = {
    "first_event_start",
    "last_event_end",
    "span_start",
    "span_end",
}
_VALID_SORT_COLS = _SORT_NUMERIC | _SORT_DATE


class StackedTimelinePlotter:
    """
    Visualize entities' timelines within their period of interest.

    One horizontal bar per entity. The bar spans their observation period.
    Event segments and occurrence markers are overlaid from a
    PipeDelimitedFormat.

    Parameters
    ----------
    pipe_delimited : PipeDelimitedFormat
        Must contain span_start and span_end columns.
    config : StackedTimelineConfig | None
        Plot configuration. Uses StackedTimelineConfig.build_with_defaults()
        if not provided.
    sort_by : list[str] | None
        Column names to sort entities by before plotting. Must exist in
        pipe_delimited.data. Common values: 'active_days', 'inactive_days',
        'inactive_days_before_first_event', 'span_duration_days',
        'first_event_start', 'last_event_end'.
        Default None — entities appear in pipe_delimited order.
    ascending : bool | list[bool]
        Sort direction. A single bool applies to all columns. A list must
        match the length of sort_by. Default True.

    Examples
    --------
    >>> plotter = StackedTimelinePlotter(pipe_delimited)
    >>> plotter.plot("output.png")

    >>> config  = StackedTimelineConfig.build_from_yaml("config.yaml")
    >>> plotter = StackedTimelinePlotter(
    ...     pipe_delimited,
    ...     config    = config,
    ...     sort_by   = ["active_days"],
    ...     ascending = [False],
    ... )
    >>> plotter.plot("output.png")
    """

    def __init__(
        self,
        pipe_delimited: PipeDelimitedFormat,
        config:    StackedTimelineConfig | None = None,
        sort_by:   list[str] | None            = None,
        ascending: bool | list[bool]           = True,
    ) -> None:
        if not isinstance(pipe_delimited, PipeDelimitedFormat):
            raise TypeError(
                f"{_ERROR_PREFIX}: pipe_delimited must be a "
                f"PipeDelimitedFormat object, "
                f"got {type(pipe_delimited).__name__}"
            )
        if (SPAN_START_COL not in pipe_delimited.data.columns or
                SPAN_END_COL not in pipe_delimited.data.columns):
            raise ValueError(
                f"{_ERROR_PREFIX}: pipe_delimited must contain "
                f"'span_start' and 'span_end' columns."
            )
        if config is None:
            config = StackedTimelineConfig.build_with_defaults()
        if not isinstance(config, StackedTimelineConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a StackedTimelineConfig "
                f"object, got {type(config).__name__}"
            )

        if sort_by is not None:
            self._validate_sort_args(sort_by, ascending, pipe_delimited.data)
            # Cast columns to correct types before sorting
            sorted_data = self._prepare_for_sort(pipe_delimited.data, sort_by)
            sorted_data = sorted_data.sort_values(
                by=sort_by, ascending=ascending, na_position="last"
            ).reset_index(drop=True)
            pipe_delimited = pipe_delimited.__class__(sorted_data, pipe_delimited.entity_col)

        self._pipe_delimited = pipe_delimited
        self._config       = config

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_sort_args(
        sort_by:   list[str],
        ascending: bool | list[bool],
        data:      pd.DataFrame,
    ) -> None:
        """
        Validate sort_by and ascending before sorting.

        Raises
        ------
        TypeError
            If sort_by is not a list of strings, or ascending is not
            a bool or list of bools.
        ValueError
            If any sort_by column is not in _VALID_SORT_COLS, does not
            exist in data, or if ascending list length does not match
            sort_by.
        """
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
        invalid = [c for c in sort_by if c not in _VALID_SORT_COLS]
        if invalid:
            raise ValueError(
                f"{_ERROR_PREFIX}: invalid sort_by column(s): {invalid}. "
                f"Valid sort columns: {sorted(_VALID_SORT_COLS)}"
            )
        missing = [c for c in sort_by if c not in data.columns]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: sort_by column(s) not found in "
                f"pipe_delimited.data: {missing}. "
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
        Cast sort columns to their correct types before sorting.

        Numeric columns are cast to float — avoids lexicographic sort
        of string-encoded numbers. Date columns are cast to datetime.
        Returns a copy with only the sort columns recast.

        Parameters
        ----------
        data : pd.DataFrame
            pipe_delimited data. Modified copy is returned.
        sort_by : list[str]
            Columns to prepare. Must all be in _VALID_SORT_COLS.

        Returns
        -------
        pd.DataFrame
            Copy of data with sort columns correctly typed.
        """
        data = data.copy()
        for col in sort_by:
            if col in _SORT_NUMERIC:
                data[col] = pd.to_numeric(data[col], errors="coerce").astype(float)
            elif col in _SORT_DATE:
                data[col] = pd.to_datetime(data[col], errors="coerce")
        return data

    # ------------------------------------------------------------------ #
    # Convenience classmethod
    # ------------------------------------------------------------------ #

    @classmethod
    def from_objects(
        cls,
        obs_period,
        events:      object | None                = None,
        occurrences: object | list[object] | None = None,
        config:      StackedTimelineConfig | None = None,
        sort_by:     list[str] | None             = None,
        ascending:   bool | list[bool]            = True,
    ) -> "StackedTimelinePlotter":
        """
        Build a StackedTimelinePlotter directly from data objects.

        Convenience classmethod that runs the analyzers, combines
        the pipe_delimited intermediates, and returns a ready-to-plot plotter.
        The pipe_delimited intermediate is never exposed — use the standard
        constructor if you need to inspect or sort it first.

        Parameters
        ----------
        obs_period : ObsPeriodPerEntity
            The observation window for each entity. Required.
        events : Events | None
            A validated Events object.
        occurrences : Occurrences | list[Occurrences] | None
            One or more validated Occurrences objects.
        config : StackedTimelineConfig | None
            Plot configuration. Uses defaults if not provided.
        sort_by : list[str] | None
            Column names to sort entities by before plotting.
            Must exist in the pipe_delimited after analyzers run.
            Common values: 'active_days', 'inactive_days',
            'inactive_days_before_first_event', 'span_duration_days',
            'first_event_start', 'last_event_end'.
            Default None — entities appear in obs_period order.
        ascending : bool | list[bool]
            Sort direction. A single bool applies to all columns. A list
            must match the length of sort_by. Default True.

        Returns
        -------
        StackedTimelinePlotter

        Examples
        --------
        >>> plotter = StackedTimelinePlotter.from_objects(
        ...     obs_period = obs,
        ...     events     = events,
        ...     sort_by    = ["active_days"],
        ...     ascending  = [False],
        ...     config     = StackedTimelineConfig.build_from_yaml("config.yaml"),
        ... )
        >>> plotter.plot("timeline.png")
        """
        pipe_delimited = PipeDelimitedFormat.from_objects(
            obs_period  = obs_period,
            events      = events,
            occurrences = occurrences,
        )
        return cls(pipe_delimited, config, sort_by=sort_by, ascending=ascending)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """Save the stacked timeline plot to a file (.png, .jpg, .jpeg)."""
        from .stacked_timeline_plotter_utils import (
            resolve_x_mode, build_span_lookup,
            precompute, format_xaxis, compute_figsize,
        )

        self._validate_path(path)

        cfg  = self._config
        gcfg = cfg.general
        ec   = self._pipe_delimited.entity_col
        data = self._pipe_delimited.data.copy()
        n    = len(data)

        if n > gcfg.max_entities:
            warnings.warn(
                f"{_ERROR_PREFIX}: {n} entities exceed "
                f"max_entities={gcfg.max_entities}. "
                f"Plot may be unreadable. Consider filtering.",
                UserWarning, stacklevel=2,
            )

        # ── Parse dates ───────────────────────────────────────────────
        data["span_start"] = pd.to_datetime(data["span_start"]).dt.normalize()
        data["span_end"]   = pd.to_datetime(data["span_end"]).dt.normalize()

        # ── Build lookups ─────────────────────────────────────────────
        span_lookup = build_span_lookup(data, ec)
        entities    = list(span_lookup.keys())
        max_days    = max(d for _, _, d in span_lookup.values())

        # ── Resolve layer configs ─────────────────────────────────────
        ev_cfg  = self._resolve_event_config()
        occ_map = self._resolve_occ_configs()

        # ── Precompute segments and markers ───────────────────────────
        bar_h = gcfg.bar_height_ratio
        color_segments, marker_groups = precompute(
            entities     = entities,
            data         = data,
            entity_col   = ec,
            span_lookup  = span_lookup,
            has_events   = self._pipe_delimited.has_events,
            ev_color     = ev_cfg.color if ev_cfg else cfg.poi_settings.color_no_events,
            occ_cfg_map  = occ_map,
            poi          = cfg.poi_settings,
            bar_h        = bar_h,
            jitter       = gcfg.jitter,
            jitter_ratio = gcfg.jitter_ratio,
        )

        # ── Figure ────────────────────────────────────────────────────
        try:
            plt.style.use(gcfg.style)
        except Exception:
            pass

        fig, ax = plt.subplots(figsize=compute_figsize(n, gcfg.row_height, gcfg.figsize))

        # ── Draw segments — one broken_barh call per color ────────────
        for color, segs in color_segments.items():
            by_y: dict[int, list] = defaultdict(list)
            for left, width, y in segs:
                by_y[y].append((left, width))
            poi_colors = {
                cfg.poi_settings.color_before,
                cfg.poi_settings.color_middle,
                cfg.poi_settings.color_after,
                cfg.poi_settings.color_no_events,
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
                    zorder     = 5,  # always above event segments (zorder=2)
                )
            else:
                y_centers = [(mn + mx) / 2 for mn, mx in zip(ymins, ymaxs)]
                ax.scatter(
                    xs, y_centers,
                    s          = size ** 2,
                    color      = color,
                    marker     = mk,
                    alpha      = alpha,
                    zorder     = 5,  # always above event segments (zorder=2)
                    linewidths = 0,
                )

        # ── Axes ──────────────────────────────────────────────────────
        ax.set_yticks(range(n))
        if gcfg.show_entity_labels:
            ax.set_yticklabels(entities, fontsize=gcfg.font_size - 2)
        else:
            ax.set_yticklabels([])
            ax.tick_params(axis="y", left=False)
        ax.set_ylim(-0.5, n - 0.5)
        ax.invert_yaxis()
        ax.set_xlim(0, max_days)

        # ── X axis ────────────────────────────────────────────────────
        x_mode         = resolve_x_mode(data, gcfg.x_axis)
        span_start_ref = data["span_start"].iloc[0] if x_mode == "calendar" else None

        format_xaxis(
            ax             = ax,
            x_mode         = x_mode,
            max_days       = max_days,
            span_start_ref = span_start_ref,
            font_size      = gcfg.font_size,
            x_cfg          = cfg.x_axis_labels,
        )

        # ── Title and legend ──────────────────────────────────────────
        ax.set_title(gcfg.title or f"Timeline — {ec}", fontsize=gcfg.title_font_size)

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
        fig.savefig(path, dpi=gcfg.dpi, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Config resolution helpers
    # ------------------------------------------------------------------ #

    def _resolve_event_config(self):
        """
        Return the first EventLayerConfig from config, or None if not
        configured. No auto-discovery — events must be explicitly configured.
        If the pipe_delimited has events but events_settings is empty,
        only the POI bar is drawn.
        """
        if not self._pipe_delimited.has_events:
            return None
        if not self._config.events_settings:
            warnings.warn(
                "[StackedTimelinePlotter] pipe_delimited has event columns "
                "but no events_settings entry found in config. "
                "Only the observation period bar will be drawn. "
                "Add an events_settings entry to show event segments.",
                UserWarning, stacklevel=3,
            )
            return None
        return self._config.events_settings[0]

    def _resolve_occ_configs(self):
        """
        Return {col: OccurrenceLayerConfig} for configured identities only.
        No auto-discovery — occurrences must be explicitly configured.
        Warns if a configured identity has no matching column in the
        pipe_delimited. Silently ignores occ_ columns not in config.
        """
        occ_map = {}
        for ocfg in self._config.occurrences_settings:
            col = f"occ_{ocfg.identity}"
            if col not in self._pipe_delimited.data.columns:
                warnings.warn(
                    f"[StackedTimelinePlotter] occurrences_settings has "
                    f"identity '{ocfg.identity}' but column '{col}' was "
                    f"not found in the pipe_delimited — skipping.",
                    UserWarning, stacklevel=3,
                )
                continue
            occ_map[col] = ocfg
        return occ_map

    def _build_legend_handles(self, ev_cfg, occ_cfg_map) -> list:
        """Build legend handle list from resolved layer configs."""
        cfg     = self._config
        poi     = cfg.poi_settings
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

    def _validate_path(self, path: str) -> None:
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
                f"Use .png, .jpg, or .jpeg"
            )

    def __repr__(self) -> str:
        return (
            f"StackedTimelinePlotter(\n"
            f"  entities    : {len(self._pipe_delimited):,}\n"
            f"  has_events  : {self._pipe_delimited.has_events}\n"
            f"  occ_columns : {self._pipe_delimited.occurrence_cols}\n"
            f"  x_axis      : '{self._config.general.x_axis}'\n"
            f")"
        )