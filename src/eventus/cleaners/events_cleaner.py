"""
events_cleaner.py
EventsCleaner — transparent, auditable cleaning of raw event data.
Produces a validated Events object with a full quality report.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from eventus.semantics.event_semantics import EventSemantics
from .events_cleaner_config import EventsCleanerConfig

_ERROR_PREFIX = "[EventsCleaner] Error"

_REASON_NULL_ENTITY   = "null_entity_id"
_REASON_NULL_DATE     = "null_date"
_REASON_PARSE_DATE    = "unparseable_date"
_REASON_BEFORE_FLOOR  = "before_date_floor"
_REASON_AFTER_CEILING = "after_date_ceiling"
_REASON_DUPLICATE     = "duplicate_row"

_VALID_CATEGORY_RULES = {"sequence", "unique"}
_VALID_NUMERIC_RULES  = {"mean", "median", "min", "max", "variance"}


class EventsCleaner:
    """
    I am a transparent, auditable pipeline that cleans raw event
    data and records every decision I make.

    Parameters
    ----------
    data : pd.DataFrame
        Raw input DataFrame — may be messy.
    semantics : EventSemantics
        Column mapping for entity_id, date, also_defined_by, and
        descriptor_cols.
    config : EventsCleanerConfig | None
        Cleaning rules. Defaults to EventsCleanerConfig() if None.
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _raw:       pd.DataFrame         # original input, never mutated
    _semantics: EventSemantics       # column mappings and identity
    _config:    EventsCleanerConfig  # cleaning rules
    _cleaned:   pd.DataFrame | None # set after .clean() is called
    _rejected:  pd.DataFrame | None # rows removed, with reason column
    _n_input:   int                 # row count of original input

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
        config:    EventsCleanerConfig | None = None,
    ) -> None:
        if not isinstance(semantics, EventSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an EventSemantics "
                f"object, got {type(semantics).__name__}"
            )
        if config is None:
            config = EventsCleanerConfig()
        if not isinstance(config, EventsCleanerConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an EventsCleanerConfig "
                f"object, got {type(config).__name__}"
            )

        self._raw       = data.copy()
        self._semantics = semantics
        self._config    = config
        self._cleaned   = None
        self._rejected  = None
        self._n_input   = len(data)

        # Validate EventConsolidateConfig against semantics
        if config.consolidate is not None:
            config.consolidate.validate_against_semantics(
                also_defined_by = semantics.also_defined_by or [],
                descriptor_cols = semantics.descriptor_cols or {},
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def clean(self) -> "Events":
        """
        Apply cleaning rules and return a validated Events object.

        Pipeline order:
        1.  Parse dates             (if config.parse_dates)
        2.  Normalize to date only  (if config.normalize_dates)
        3.  Reject null entity IDs
        4.  Reject null or unparseable dates
        5.  Reject rows outside date_floor / date_ceiling
        6.  Drop duplicate rows     (if config.drop_duplicate_rows)
        7.  Consolidate             (if config.consolidate is not None)

        Returns
        -------
        Events
            A validated Events object containing only clean rows.
        """
        from eventus.data_objects.events import Events

        df  = self._raw.copy()
        ec  = self._semantics.entity_id_col
        dc  = self._semantics.date_col
        cfg = self._config

        # Validate required columns exist
        for col, label in [(ec, "entity"), (dc, "date")]:
            if col not in df.columns:
                raise ValueError(
                    f"{_ERROR_PREFIX}: {label} column '{col}' not found "
                    f"in data. Available: {sorted(df.columns.tolist())}"
                )

        rejected_frames = []

        # ── 1. Parse dates ────────────────────────────────────────────────
        if cfg.parse_dates:
            parsed = pd.to_datetime(df[dc], errors="coerce")
            bad    = df[parsed.isna() & df[dc].notna()].copy()
            if len(bad) > 0:
                bad["_rejection_reason"] = _REASON_PARSE_DATE
                rejected_frames.append(bad)
                df = df[~(parsed.isna() & df[dc].notna())].copy()
            df[dc] = pd.to_datetime(df[dc], errors="coerce")
        else:
            df[dc] = pd.to_datetime(df[dc], errors="coerce")

        # ── 2. Normalize to date only ─────────────────────────────────────
        if cfg.normalize_dates:
            df[dc] = df[dc].dt.normalize()

        # ── 3. Null entity ID ─────────────────────────────────────────────
        mask = df[ec].isna()
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_NULL_ENTITY
            rejected_frames.append(bad)
            df = df[~mask].copy()

        # ── 4. Null date ──────────────────────────────────────────────────
        mask = df[dc].isna()
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_NULL_DATE
            rejected_frames.append(bad)
            df = df[~mask].copy()

        # ── 5. Date floor / ceiling ───────────────────────────────────────
        floor   = pd.Timestamp(cfg.date_floor)
        ceiling = pd.Timestamp(cfg.date_ceiling)

        mask = df[dc] < floor
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_BEFORE_FLOOR
            rejected_frames.append(bad)
            df = df[~mask].copy()

        mask = df[dc] > ceiling
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_AFTER_CEILING
            rejected_frames.append(bad)
            df = df[~mask].copy()

        # ── 6. Drop duplicate rows ────────────────────────────────────────
        if cfg.drop_duplicate_rows:
            dupes = df.duplicated(keep="first")
            if dupes.any():
                bad = df[dupes].copy()
                bad["_rejection_reason"] = _REASON_DUPLICATE
                rejected_frames.append(bad)
                df = df[~dupes].copy()

        # ── Combine rejected ──────────────────────────────────────────────
        self._rejected = (
            pd.concat(rejected_frames, ignore_index=True)
            if rejected_frames
            else pd.DataFrame(columns=list(df.columns) + ["_rejection_reason"])
        )

        self._cleaned = df.reset_index(drop=True)

        # Rows that survived rejection, before consolidation folds same-date
        # records together.
        self._n_surviving_before_consolidate = len(self._cleaned)

        # ── 7. Consolidate same-date records ──────────────────────────────
        if cfg.consolidate is not None and len(self._cleaned) > 0:
            self._cleaned = self._consolidate(self._cleaned)

        return Events._construct_from_cleaned(self._cleaned, self._semantics)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def rejected(self) -> pd.DataFrame:
        """Rows that were removed, with _rejection_reason column."""
        self._require_cleaned("rejected")
        return self._rejected.copy()

    # ------------------------------------------------------------------ #
    # Quality report
    # ------------------------------------------------------------------ #

    def print_report(self) -> None:
        """Print a structured summary of the cleaning results."""
        self._require_cleaned("print_report")

        n_clean    = len(self._cleaned)
        n_rejected = len(self._rejected)
        n_total    = self._n_input
        # Rows folded into surviving events by consolidation — combined, not
        # discarded. Reconciliation: total = rejected + consolidated_away + clean
        n_surviving = getattr(self, "_n_surviving_before_consolidate", n_clean)
        n_consolidated_away = n_surviving - n_clean

        print(f"Cleaning report — events")
        print(f"{'─' * 56}")
        print(f"{'Total input rows:':<42} {n_total:>8,}")
        print(f"{'─' * 56}")

        if n_rejected > 0:
            print(f"  Rejected:")
            counts = (
                self._rejected["_rejection_reason"]
                .value_counts().reset_index()
            )
            counts.columns = ["reason", "n"]
            for _, row in counts.iterrows():
                label = f"    {row['reason']}:"
                print(
                    f"{label:<44} {int(row['n']):>6,}"
                    f"   ({round(100 * row['n'] / n_total, 1)}%)"
                )
        else:
            print(f"  No rows rejected")

        print(f"{'─' * 56}")
        print(
            f"{'Total rejected:':<42} {n_rejected:>8,}"
            f"   ({round(100 * n_rejected / n_total, 1)}%)"
        )
        if n_consolidated_away > 0:
            print(
                f"{'Consolidated into other events:':<42} {n_consolidated_away:>8,}"
                f"   ({round(100 * n_consolidated_away / n_total, 1)}%)"
            )
        print(
            f"{'Clean rows:':<42} {n_clean:>8,}"
            f"   ({round(100 * n_clean / n_total, 1)}%)"
        )
        if self._config.consolidate is not None:
            print(f"  (clean rows are consolidated events)")

    def quality_report_df(self) -> pd.DataFrame:
        """Return quality report as a DataFrame."""
        self._require_cleaned("quality_report_df")

        n_total = self._n_input
        rows    = []

        if len(self._rejected) > 0:
            counts = (
                self._rejected["_rejection_reason"]
                .value_counts().reset_index()
            )
            counts.columns = ["reason", "n"]
            counts["action"]       = "rejected"
            counts["pct_of_input"] = (counts["n"] / n_total * 100).round(1)
            rows.extend(counts.to_dict("records"))

        n_surviving = getattr(self, "_n_surviving_before_consolidate", len(self._cleaned))
        n_consolidated_away = n_surviving - len(self._cleaned)
        if n_consolidated_away > 0:
            rows.append({
                "reason":       "CONSOLIDATED_INTO_OTHER_EVENTS",
                "n":            n_consolidated_away,
                "action":       "merged",
                "pct_of_input": round(100 * n_consolidated_away / n_total, 1),
            })

        rows.append({
            "reason":       "CLEAN",
            "n":            len(self._cleaned),
            "action":       "kept",
            "pct_of_input": round(100 * len(self._cleaned) / n_total, 1),
        })

        return pd.DataFrame(rows)[["reason", "action", "n", "pct_of_input"]]

    # ------------------------------------------------------------------ #
    # Consolidation
    # ------------------------------------------------------------------ #

    def _consolidate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Consolidate same-date records into one event per
        entity + date + also_defined_by group.
        """
        ec              = self._semantics.entity_id_col
        dc              = self._semantics.date_col
        also_defined_by = self._semantics.also_defined_by or []
        consolidate_cfg = self._config.consolidate
        sem_descriptors = self._semantics.descriptor_cols or {}

        group_cols = [ec, dc] + [
            col for col in also_defined_by if col in df.columns
        ]
        agg_cols = [
            col for col in sem_descriptors.keys()
            if col in df.columns and col not in group_cols
        ]

        consolidated = []

        for group_values, group in df.groupby(group_cols, sort=False):
            if isinstance(group_values, tuple):
                row = dict(zip(group_cols, group_values))
            else:
                row = {group_cols[0]: group_values}

            for col in agg_cols:
                rule     = consolidate_cfg.descriptor_cols.get(col, "sequence")
                col_type = sem_descriptors[col].type
                values   = [str(v) for v in group[col].tolist()]

                if col_type == "numeric" and rule in _VALID_NUMERIC_RULES:
                    nums = []
                    for v in values:
                        try:
                            nums.append(float(v))
                        except (ValueError, TypeError):
                            pass
                    if nums:
                        arr = np.array(nums)
                        if rule == "mean":     row[col] = float(np.mean(arr))
                        elif rule == "median": row[col] = float(np.median(arr))
                        elif rule == "min":    row[col] = float(np.min(arr))
                        elif rule == "max":    row[col] = float(np.max(arr))
                        elif rule == "variance": row[col] = float(np.var(arr))
                    else:
                        row[col] = None
                else:
                    clean = [v for v in values if v not in ("nan", "None", "")]
                    if rule == "unique":
                        row[col] = " | ".join(sorted(set(clean))) if clean else ""
                    else:
                        row[col] = " | ".join(clean) if clean else ""

            consolidated.append(row)

        return pd.DataFrame(consolidated).reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_cleaned(self, method_name: str) -> None:
        if self._cleaned is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires calling "
                f".clean() first."
            )

    def __repr__(self) -> str:
        status = "cleaned" if self._cleaned is not None else "not yet cleaned"
        return (
            f"EventsCleaner(\n"
            f"  input rows : {self._n_input:,}\n"
            f"  status     : {status}\n"
            f"  config     : {self._config.__class__.__name__}\n"
            f")"
        )
