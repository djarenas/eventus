"""
viz_stacked_events.py
StackedEventsPlotter — draws one horizontal bar per entity showing
event intervals within a span, with optional occurrence markers.
Accepts a PipeDelimitedIntermediate (or any subclass) as input.
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
from collections import defaultdict

_ERROR_PREFIX = "[StackedEventsPlotter] Error"

_REQUIRED_CONFIG_KEYS  = {"general", "colors", "occurrences"}
_REQUIRED_GENERAL_KEYS = {"row_height", "bar_height_ratio", "dpi",
                           "font_size", "title_font_size", "style"}
_REQUIRED_COLOR_KEYS   = {"before", "active", "middle", "after", "no_coverage"}
_REQUIRED_OCC_KEYS     = {"identity", "color", "thickness"}


class StackedEventsPlotter:
    """
    Draws one horizontal bar per entity showing event intervals within a span.
    Optionally overlays occurrence markers as vertical lines.

    Pure renderer — does not transform, clip, merge, or analyze data.
    Accepts a PipeDelimitedIntermediate (or subclass) as the primary input.
    Events outside the span are not drawn. Occurrences outside the span
    are not drawn.

    Parameters
    ----------
    config_path : str
        Path to a stacked_events_config.yaml file.
    intermediate : PipeDelimitedIntermediate
        Required. Must have span columns (span_start + span_end).
    occurrences : list | None
        Optional Occurrences objects to overlay as markers.
        Each must have an identity matching a config entry.
    entity_order : list | None
        Explicit entity order for bars. Entities not in the list are dropped.
        If None, drawn in the order they appear in intermediate.data.
    n_sample : int | None
        If provided, randomly sample this many entities.
    random_state : int | None
        Random seed for reproducible sampling.
    """

    def __init__(
        self,
        config_path: str,
        intermediate,
        occurrences: list | None = None,
        sort_by: list | None = None,
        ascending: bool | list = True,
        n_sample: int | None = None,
        random_state: int | None = None,
    ) -> None:
        from .pipe_delimited_intermediate import PipeDelimitedIntermediate

        # --- Load and validate config ---
        self._cfg = self._load_config(config_path)

        # --- Validate intermediate ---
        if not isinstance(intermediate, PipeDelimitedIntermediate):
            raise TypeError(
                f"{_ERROR_PREFIX}: intermediate must be a PipeDelimitedIntermediate "
                f"or subclass, got {type(intermediate).__name__}"
            )
        if not intermediate.has_spans:
            raise ValueError(
                f"{_ERROR_PREFIX}: intermediate must have span_start and span_end columns"
            )
        self._intermediate = intermediate
        self._entity_col   = intermediate.entity_col

        # --- Must have something to draw ---
        has_events      = intermediate.has_events
        has_occ_cols    = len(intermediate.occurrence_cols) > 0
        has_occ_objects = occurrences is not None and len(occurrences) > 0
        if not has_events and not has_occ_cols and not has_occ_objects:
            raise ValueError(
                f"{_ERROR_PREFIX}: intermediate has no event or occurrence data to plot"
            )

        # --- Validate occurrences objects ---
        occurrences    = occurrences or []
        cfg_identities = {o["identity"] for o in self._cfg["occurrences"]}
        for occ in occurrences:
            identity = getattr(getattr(occ, "semantics", None), "identity", None)
            if identity is None:
                raise ValueError(
                    f"{_ERROR_PREFIX}: an Occurrences object has no identity — "
                    f"set it in OccurrenceSemantics"
                )
            if identity not in cfg_identities:
                raise ValueError(
                    f"{_ERROR_PREFIX}: Occurrences identity '{identity}' not found "
                    f"in config. Available: {sorted(cfg_identities)}"
                )
            if occ.semantics.entity_id_col != self._entity_col:
                raise ValueError(
                    f"{_ERROR_PREFIX}: Occurrences '{identity}' has entity_id_col "
                    f"'{occ.semantics.entity_id_col}' but expected '{self._entity_col}'"
                )
        self._occurrences = occurrences

        # --- Validate occ_* columns in intermediate against config ---
        cfg_identities_lower = {
            o["identity"].lower().replace(" ", "_"): o["identity"]
            for o in self._cfg["occurrences"]
        }
        for col in intermediate.occurrence_cols:
            col_key = col[4:]
            if col_key not in cfg_identities_lower:
                raise ValueError(
                    f"{_ERROR_PREFIX}: intermediate has occurrence column '{col}' "
                    f"but no matching config entry found. "
                    f"Available: {sorted(cfg_identities)}"
                )

        # --- Validate sort_by columns ---
        if sort_by is not None:
            invalid = [c for c in sort_by if c not in intermediate.data.columns]
            if invalid:
                raise ValueError(
                    f"{_ERROR_PREFIX}: sort_by contains unknown columns: {invalid}. "
                    f"Available: {sorted(intermediate.data.columns.tolist())}"
                )

        # --- Store params ---
        self._sort_by      = sort_by
        self._ascending    = ascending
        self._n_sample     = n_sample
        self._random_state = random_state

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """Render and save the stacked bar chart (.png, .jpg, .jpeg)."""
        ext = pathlib.Path(path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(
                f"{_ERROR_PREFIX}: unsupported extension '{ext}'. "
                "Use .png, .jpg, or .jpeg"
            )
        entities, span_lookup = self._build_entity_list()
        all_segments, all_markers = self._precompute(entities, span_lookup)
        fig = self._render(entities, span_lookup, all_segments, all_markers)
        fig.savefig(path, dpi=self._cfg["general"]["dpi"], bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Step 1 — build entity list and span lookup
    # ------------------------------------------------------------------ #

    def _build_entity_list(self) -> tuple[list, dict]:
        """Build ordered entity list and span lookup dict — vectorized."""
        col  = self._entity_col
        data = self._intermediate.data.copy()
        data = data[data[col].notna()]

        # Vectorized span parsing
        span_starts = pd.to_datetime(data["span_start"]).dt.normalize()
        span_ends   = pd.to_datetime(data["span_end"]).dt.normalize()

        span_lookup = dict(zip(
            data[col].tolist(),
            zip(span_starts.tolist(), span_ends.tolist())
        ))

        entities = list(span_lookup.keys())

        # Sample first
        if self._n_sample is not None and self._n_sample < len(entities):
            import random
            rng = random.Random(self._random_state)
            entities = rng.sample(entities, self._n_sample)

        # Then sort
        if self._sort_by is not None:
            col = self._entity_col
            sub = self._intermediate.data[
                self._intermediate.data[col].isin(entities)
            ].sort_values(
                by=self._sort_by,
                ascending=self._ascending,
                na_position="last",
            )
            entities = sub[col].tolist()

        return entities, span_lookup

    # ------------------------------------------------------------------ #
    # Step 2 — precompute all segments and markers
    # ------------------------------------------------------------------ #

    def _precompute(
        self,
        entities: list,
        span_lookup: dict,
    ) -> tuple[dict, dict]:
        """
        Pre-index data and compute all segments + markers for all entities.

        Returns
        -------
        all_segments : dict[entity -> list[(left, width, color)]]
        all_markers  : dict[entity -> list[(day_offset, color, thickness)]]
        """
        col  = self._entity_col
        data = self._intermediate.data

        # Pre-index by entity for O(1) lookup
        entity_index = {
            entity: data[data[col] == entity].iloc[0]
            for entity in entities
            if (data[col] == entity).any()
        }

        cfg       = self._cfg["colors"]
        cfg_lower = {
            o["identity"].lower().replace(" ", "_"): o
            for o in self._cfg["occurrences"]
        }
        occ_cfg = {o["identity"]: o for o in self._cfg["occurrences"]}

        # Pre-index Occurrences objects by entity
        occ_by_entity = defaultdict(list)
        for occ in self._occurrences:
            date_col  = occ.semantics.date_col
            identity  = occ.semantics.identity
            cfg_entry = occ_cfg[identity]
            for _, orow in occ.data.iterrows():
                entity = orow[col]
                if entity in span_lookup:
                    occ_by_entity[entity].append((
                        pd.Timestamp(orow[date_col]).normalize(),
                        cfg_entry["color"],
                        cfg_entry["thickness"],
                    ))

        all_segments = {}
        all_markers  = {}

        for entity in entities:
            span_start, span_end = span_lookup[entity]
            span_days = (span_end - span_start).days
            row = entity_index.get(entity)

            # --- Segments ---
            if row is None or not self._intermediate.has_events or pd.isna(row.get("event_starts")):
                all_segments[entity] = [(0, span_days, cfg["no_coverage"])]
            else:
                all_segments[entity] = self._parse_segments(
                    row, span_start, span_end, span_days, cfg
                )

            # --- Markers from occ_* columns ---
            markers = []
            if row is not None:
                for occ_col in self._intermediate.occurrence_cols:
                    col_key   = occ_col[4:]
                    cfg_entry = cfg_lower.get(col_key)
                    if cfg_entry is None:
                        continue
                    val = row.get(occ_col)
                    if pd.isna(val):
                        continue
                    for token in str(val).split(" | "):
                        try:
                            d = pd.Timestamp(token.strip()).normalize()
                        except Exception:
                            continue
                        if span_start <= d <= span_end:
                            markers.append((
                                (d - span_start).days,
                                cfg_entry["color"],
                                cfg_entry["thickness"],
                            ))

            # --- Markers from Occurrences objects ---
            for d, color, thickness in occ_by_entity.get(entity, []):
                if span_start <= d <= span_end:
                    markers.append(((d - span_start).days, color, thickness))

            all_markers[entity] = markers

        return all_segments, all_markers

    def _parse_segments(
        self,
        row: pd.Series,
        span_start: pd.Timestamp,
        span_end: pd.Timestamp,
        span_days: int,
        cfg: dict,
    ) -> list[tuple[float, float, str]]:
        """Parse pipe-delimited event strings into color segments."""
        starts_raw = str(row["event_starts"]).split(" | ")
        ends_raw   = str(row["event_ends"]).split(" | ")

        intervals = []
        for s, e in zip(starts_raw, ends_raw):
            try:
                ev_start = pd.Timestamp(s.strip()).normalize()
                ev_end   = pd.Timestamp(e.strip()).normalize()
            except Exception:
                continue
            if ev_start < span_end and ev_end > span_start:
                intervals.append((
                    max(ev_start, span_start),
                    min(ev_end,   span_end),
                ))

        if not intervals:
            return [(0, span_days, cfg["no_coverage"])]

        intervals.sort(key=lambda x: x[0])
        segments      = []
        prev_end_days = 0.0

        for ev_start, ev_end in intervals:
            left_days  = (ev_start - span_start).days
            right_days = (ev_end   - span_start).days
            width_days = right_days - left_days

            if left_days > prev_end_days:
                gap_w = left_days - prev_end_days
                color = cfg["before"] if prev_end_days == 0.0 else cfg["middle"]
                segments.append((prev_end_days, gap_w, color))

            if width_days > 0:
                segments.append((left_days, width_days, cfg["active"]))

            prev_end_days = max(prev_end_days, right_days)

        if prev_end_days < span_days:
            segments.append((prev_end_days, span_days - prev_end_days, cfg["after"]))

        return segments

    # ------------------------------------------------------------------ #
    # Step 3 — render using broken_barh (one call per color)
    # ------------------------------------------------------------------ #

    def _render(
        self,
        entities: list,
        span_lookup: dict,
        all_segments: dict,
        all_markers: dict,
    ) -> plt.Figure:
        """
        Render using broken_barh — groups all segments by color and draws
        each color in a single matplotlib call instead of one call per segment.
        """
        cfg      = self._cfg
        gcfg     = cfg["general"]
        fs       = gcfg["font_size"]
        title_fs = gcfg["title_font_size"]

        try:
            plt.style.use(gcfg["style"])
        except Exception:
            pass

        n       = len(entities)
        row_h   = gcfg["row_height"]        # inches per row
        fig_h   = max(2.0, n * row_h + 1.5) # total figure height
        fig, ax = plt.subplots(figsize=(12, fig_h))

        # bar_h in data coordinates: ratio * 1.0 (rows are spaced 1 unit apart)
        bar_h   = gcfg["bar_height_ratio"]  # 1.0 = full row, no gap

        # Group segments by color across all entities for broken_barh
        # broken_barh format: list of (xstart, xwidth) per y position
        color_segments: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
        # (xstart, xwidth, y_center)

        for i, entity in enumerate(entities):
            y_center = i
            for left, width, color in all_segments[entity]:
                if width > 0:
                    color_segments[color].append((left, width, y_center))

        # Draw all segments of each color in one broken_barh call
        for color, segs in color_segments.items():
            # Group by y_center for broken_barh
            by_y: dict[float, list[tuple[float, float]]] = defaultdict(list)
            for left, width, y_center in segs:
                by_y[y_center].append((left, width))

            for y_center, xranges in by_y.items():
                ax.broken_barh(xranges, (y_center - bar_h / 2, bar_h),
                               facecolors=color)

        # Draw occurrence markers — group by color for vlines batch call
        marker_by_color: dict[str, tuple[list, list, list]] = defaultdict(
            lambda: ([], [], [])  # xs, ymins, ymaxs
        )
        for i, entity in enumerate(entities):
            y_center = i
            for day_offset, color, thickness in all_markers[entity]:
                xs, ymins, ymaxs = marker_by_color[(color, thickness)]
                xs.append(day_offset)
                ymins.append(y_center - bar_h / 2)
                ymaxs.append(y_center + bar_h / 2)

        for (color, thickness), (xs, ymins, ymaxs) in marker_by_color.items():
            if xs:
                ax.vlines(x=xs, ymin=ymins, ymax=ymaxs,
                          colors=color, linewidths=thickness)

        # Axes formatting
        ax.set_yticks(range(n))
        ax.set_yticklabels([])
        ax.tick_params(axis="y", left=False)
        ax.tick_params(axis="x", labelsize=fs - 1)
        ax.set_xlabel("Days since span start", fontsize=fs)

        title = gcfg.get("title") or f"{self._entity_col} (n={n})"
        ax.set_title(title, fontsize=title_fs)
        ax.set_xlim(0, max(
            (span_end - span_start).days
            for span_start, span_end in span_lookup.values()
        ))
        ax.set_ylim(-0.5, n - 0.5)

        # Legend
        legend_elements = [
            mpatches.Patch(facecolor=cfg["colors"]["before"],      label="Inactive before first event"),
            mpatches.Patch(facecolor=cfg["colors"]["active"],      label="Active"),
            mpatches.Patch(facecolor=cfg["colors"]["middle"],      label="Gaps"),
            mpatches.Patch(facecolor=cfg["colors"]["after"],       label="Inactive after last event"),
            mpatches.Patch(facecolor=cfg["colors"]["no_coverage"], label="No coverage"),
        ]
        occ_cfg_map = {o["identity"]: o for o in cfg["occurrences"]}
        seen = set()
        for occ in self._occurrences:
            identity = occ.semantics.identity
            if identity not in seen:
                entry = occ_cfg_map[identity]
                legend_elements.append(
                    mpatches.Patch(facecolor=entry["color"], label=identity)
                )
                seen.add(identity)

        ax.legend(handles=legend_elements, loc="upper center",
                  bbox_to_anchor=(0.5, -0.05), ncol=3,
                  fontsize=fs - 1, frameon=False)

        fig.tight_layout()
        fig.subplots_adjust(bottom=0.12)
        return fig

    # ------------------------------------------------------------------ #
    # Config loading and validation
    # ------------------------------------------------------------------ #

    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError(f"{_ERROR_PREFIX}: config at '{path}' must be a YAML mapping")
        missing = _REQUIRED_CONFIG_KEYS - set(cfg.keys())
        if missing:
            raise ValueError(f"{_ERROR_PREFIX}: config missing sections: {sorted(missing)}")
        missing_g = _REQUIRED_GENERAL_KEYS - set(cfg["general"].keys())
        if missing_g:
            raise ValueError(f"{_ERROR_PREFIX}: config general section missing keys: {sorted(missing_g)}")
        missing_c = _REQUIRED_COLOR_KEYS - set(cfg["colors"].keys())
        if missing_c:
            raise ValueError(f"{_ERROR_PREFIX}: config colors section missing keys: {sorted(missing_c)}")
        for i, occ in enumerate(cfg.get("occurrences", [])):
            missing_o = _REQUIRED_OCC_KEYS - set(occ.keys())
            if missing_o:
                raise ValueError(
                    f"{_ERROR_PREFIX}: occurrences entry {i} missing keys: {sorted(missing_o)}"
                )
        return cfg
