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
    Visualize entities' timelines within their period of interest.

    One horizontal bar per entity. The bar spans their observation period.
    Event segments and occurrence markers are overlaid from a
    PipeDelimitedIntermediate.

    Parameters
    ----------
    intermediate : PipeDelimitedIntermediate
        Must contain span_start and span_end columns.
    config : StackedTimelineConfig | None
        Plot configuration. Uses StackedTimelineConfig.build_with_defaults()
        if not provided.

    Examples
    --------
    >>> plotter = StackedTimelinePlotter(combined)
    >>> plotter.plot("output.png")

    >>> config  = StackedTimelineConfig.build_from_yaml("config.yaml")
    >>> plotter = StackedTimelinePlotter(combined, config)
    >>> plotter.plot("output.png")
    """

    def __init__(self, intermediate, config=None) -> None:
        from intermediates.pipe_delimited_intermediate import (
            PipeDelimitedIntermediate,
            SPAN_START_COL, SPAN_END_COL,
        )
        from .stacked_timeline_config import StackedTimelineConfig

        if not isinstance(intermediate, PipeDelimitedIntermediate):
            raise TypeError(
                f"{_ERROR_PREFIX}: intermediate must be a "
                f"PipeDelimitedIntermediate object, "
                f"got {type(intermediate).__name__}"
            )
        if (SPAN_START_COL not in intermediate.data.columns or
                SPAN_END_COL not in intermediate.data.columns):
            raise ValueError(
                f"{_ERROR_PREFIX}: intermediate must contain "
                f"'span_start' and 'span_end' columns."
            )
        if config is None:
            config = StackedTimelineConfig.build_with_defaults()
        if not isinstance(config, StackedTimelineConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be a StackedTimelineConfig "
                f"object, got {type(config).__name__}"
            )

        self._intermediate = intermediate
        self._config       = config

    # ------------------------------------------------------------------ #
    # Convenience classmethod
    # ------------------------------------------------------------------ #

    @classmethod
    def from_objects(
        cls,
        obs_period,
        events      = None,
        occurrences = None,
        config      = None,
        sort_by     = None,
        ascending   = True,
    ) -> "StackedTimelinePlotter":
        """
        Build a StackedTimelinePlotter directly from data objects.

        Convenience classmethod that runs the analyzers, combines
        the intermediates, and returns a ready-to-plot plotter.
        The intermediate is never exposed — use the standard
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
            Must exist in the intermediate after analyzers run.
            Common values: 'active_days', 'inactive_days',
            'inactive_days_before_first_event', 'span_duration_days',
            'first_event_start', 'last_event_end'.
            Default None — entities appear in obs_period order.
        ascending : bool | list[bool]
            Sort direction. Default True.

        Returns
        -------
        StackedTimelinePlotter

        Examples
        --------
        >>> # Sort by most active days first
        >>> plotter = StackedTimelinePlotter.from_objects(
        ...     obs_period = obs,
        ...     events     = events,
        ...     sort_by    = ["active_days"],
        ...     ascending  = [False],
        ...     config     = StackedTimelineConfig.build_from_yaml("config.yaml"),
        ... )
        >>> plotter.plot("timeline.png")
        """
        from intermediates.pipe_delimited_intermediate import PipeDelimitedIntermediate

        if sort_by is not None and not isinstance(sort_by, list):
            raise TypeError(
                f"{_ERROR_PREFIX} in from_objects(): sort_by must be a "
                f"list of column name strings or None, "
                f"got {type(sort_by).__name__}"
            )

        intermediate = PipeDelimitedIntermediate.from_objects(
            obs_period  = obs_period,
            events      = events,
            occurrences = occurrences,
        )

        if sort_by is not None:
            intermediate = intermediate.sort(by=sort_by, ascending=ascending)

        return cls(intermediate, config)

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
        ec   = self._intermediate.entity_col
        data = self._intermediate.data.copy()
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
            entities    = entities,
            data        = data,
            entity_col  = ec,
            span_lookup = span_lookup,
            has_events  = self._intermediate.has_events,
            ev_color    = ev_cfg.color if ev_cfg else cfg.poi_settings.color_no_events,
            occ_cfg_map = occ_map,
            poi         = cfg.poi_settings,
            bar_h       = bar_h,
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
                    zorder     = 3,
                )
            else:
                y_centers = [(mn + mx) / 2 for mn, mx in zip(ymins, ymaxs)]
                ax.scatter(
                    xs, y_centers,
                    s          = size ** 2,
                    color      = color,
                    marker     = mk,
                    alpha      = alpha,
                    zorder     = 3,
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
        If the intermediate has events but events_settings is empty,
        only the POI bar is drawn.
        """
        if not self._intermediate.has_events:
            return None
        if not self._config.events_settings:
            warnings.warn(
                "[StackedTimelinePlotter] Intermediate has event columns "
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
        intermediate. Silently ignores occ_ columns not in config.
        """
        occ_map = {}
        for ocfg in self._config.occurrences_settings:
            col = f"occ_{ocfg.identity}"
            if col not in self._intermediate.data.columns:
                warnings.warn(
                    f"[StackedTimelinePlotter] occurrences_settings has "
                    f"identity '{ocfg.identity}' but column '{col}' was "
                    f"not found in the intermediate — skipping.",
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
            f"  entities    : {len(self._intermediate):,}\n"
            f"  has_events  : {self._intermediate.has_events}\n"
            f"  occ_columns : {self._intermediate.occurrence_cols}\n"
            f"  x_axis      : '{self._config.general.x_axis}'\n"
            f")"
        )