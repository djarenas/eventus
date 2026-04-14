"""
events_cleaner.py
EventsCleaner — transparent, auditable cleaning of raw event data.
Produces a validated Events object with a full quality report.
"""
from __future__ import annotations
import sys
import pandas as pd


from .events_cleaner_config import EventsCleanerConfig

# Add the inner package folder directly to sys.path  
sys.path.append(r"C:/Users/DanielArenas/Desktop/Github_Local/Python_Events_Classes")  
from semantics.event_semantics import EventSemantics


_ERROR_PREFIX = "[EventsCleaner] Error"

# Rejection / action reasons
_REASON_NULL_ENTITY        = "null_entity_id"
_REASON_NULL_START         = "null_start_date"
_REASON_NULL_END           = "null_end_date"
_REASON_PARSE_START        = "unparseable_start_date"
_REASON_PARSE_END          = "unparseable_end_date"
_REASON_BEFORE_FLOOR       = "before_date_floor"
_REASON_AFTER_CEILING      = "after_date_ceiling"
_REASON_CAUSALITY_REJECTED = "end_before_start_rejected"
_REASON_CAUSALITY_SWAPPED  = "end_before_start_swapped"
_REASON_COALESCED_START    = "start_coalesced_from_end"
_REASON_COALESCED_END      = "end_coalesced_from_start"
_REASON_DUPLICATE          = "duplicate_row"


class EventsCleaner:
    """
    Transparent, auditable cleaning of raw event data.

    Applies configurable cleaning rules to a raw DataFrame and produces
    a validated Events object. Every rejected or modified row is recorded
    with an explicit reason. Call quality_report() to see a full summary
    of what happened and why.

    Parameters
    ----------
    data : pd.DataFrame
        Raw input DataFrame — may be messy.
    semantics : EventSemantics
        Column mapping for entity_id, start_time, end_time.
    config : EventsCleanerConfig | None
        Cleaning rules. Defaults to EventsCleanerConfig() if not provided.

    Examples
    --------
    >>> cleaner = EventsCleaner(raw_df, sem)
    >>> events  = cleaner.clean()
    >>> cleaner.quality_report()

    >>> config  = EventsCleanerConfig.build_from_yaml("cleaner.yaml")
    >>> cleaner = EventsCleaner(raw_df, sem, config)
    >>> events  = cleaner.clean()
    """

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
        config:    EventsCleanerConfig | None = None,
    ) -> None:
        if not isinstance(semantics, EventSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an EventSemantics object, "
                f"got {type(semantics).__name__}"
            )
        if config is None:
            config = EventsCleanerConfig()
        if not isinstance(config, EventsCleanerConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an EventsCleanerConfig object, "
                f"got {type(config).__name__}"
            )

        self._raw       = data.copy()
        self._semantics = semantics
        self._config    = config
        self._cleaned   = None
        self._rejected  = None
        self._modified  = None   # rows kept but modified (coalesced, swapped)
        self._n_input   = len(data)

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
        4.  Coalesce missing dates  (if config.coalesce_dates)
            or reject null start/end
        5.  Reject rows outside date_floor / date_ceiling
        6.  Causality check         (reject or swap end < start)
        7.  Drop exact duplicates   (if config.drop_duplicates)
        8.  Merge overlapping       (if config.merge_overlapping)

        Returns
        -------
        Events
            A validated Events object containing only clean rows.
        """
        from data_objects.events import Events
        from data_objects.events_utils import merge_overlapping_events

        df  = self._raw.copy()
        ec  = self._semantics.entity_id_col
        sc  = self._semantics.start_time_col
        en  = self._semantics.end_time_col
        cfg = self._config

        rejected_frames = []
        modified_frames = []

        # ── 1. Parse dates ────────────────────────────────────────────────
        if cfg.parse_dates:
            for col, reason in [(sc, _REASON_PARSE_START), (en, _REASON_PARSE_END)]:
                if col in df.columns:
                    parsed = pd.to_datetime(df[col], errors="coerce")
                    bad    = df[parsed.isna() & df[col].notna()].copy()
                    if len(bad) > 0:
                        bad["_rejection_reason"] = reason
                        rejected_frames.append(bad)
                        df = df[~(parsed.isna() & df[col].notna())].copy()
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            for col in [sc, en]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

        # ── 2. Normalize to date only ─────────────────────────────────────
        if cfg.normalize_dates:
            for col in [sc, en]:
                if col in df.columns:
                    df[col] = df[col].dt.normalize()

        # ── 3. Null entity ID ─────────────────────────────────────────────
        mask = df[ec].isna()
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_NULL_ENTITY
            rejected_frames.append(bad)
            df = df[~mask].copy()

        # ── 4. Coalesce or reject null start/end ──────────────────────────
        if cfg.coalesce_dates:
            # Coalesce start from end
            missing_start = df[sc].isna() & df[en].notna()
            if missing_start.any():
                modified = df[missing_start].copy()
                df.loc[missing_start, sc] = df.loc[missing_start, en]
                modified["_rejection_reason"] = _REASON_COALESCED_START
                modified_frames.append(modified)

            # Coalesce end from start
            missing_end = df[en].isna() & df[sc].notna()
            if missing_end.any():
                modified = df[missing_end].copy()
                df.loc[missing_end, en] = df.loc[missing_end, sc]
                modified["_rejection_reason"] = _REASON_COALESCED_END
                modified_frames.append(modified)

            # Still reject if both are null
            for col, reason in [(sc, _REASON_NULL_START), (en, _REASON_NULL_END)]:
                mask = df[col].isna()
                if mask.any():
                    bad = df[mask].copy()
                    bad["_rejection_reason"] = reason
                    rejected_frames.append(bad)
                    df = df[~mask].copy()
        else:
            # Reject any null start or end
            for col, reason in [(sc, _REASON_NULL_START), (en, _REASON_NULL_END)]:
                mask = df[col].isna()
                if mask.any():
                    bad = df[mask].copy()
                    bad["_rejection_reason"] = reason
                    rejected_frames.append(bad)
                    df = df[~mask].copy()

        # ── 5. Date floor / ceiling ───────────────────────────────────────
        floor   = pd.Timestamp(cfg.date_floor)
        ceiling = pd.Timestamp(cfg.date_ceiling)

        mask = df[sc] < floor
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_BEFORE_FLOOR
            rejected_frames.append(bad)
            df = df[~mask].copy()

        mask = df[en] > ceiling
        if mask.any():
            bad = df[mask].copy()
            bad["_rejection_reason"] = _REASON_AFTER_CEILING
            rejected_frames.append(bad)
            df = df[~mask].copy()

        # ── 6. Causality check ────────────────────────────────────────────
        bad_causality = df[en] < df[sc]
        if bad_causality.any():
            if cfg.causality_check == "swap":
                modified = df[bad_causality].copy()
                modified["_rejection_reason"] = _REASON_CAUSALITY_SWAPPED
                modified_frames.append(modified)
                # Swap start and end
                df.loc[bad_causality, [sc, en]] = (
                    df.loc[bad_causality, [en, sc]].values
                )
            else:  # reject
                bad = df[bad_causality].copy()
                bad["_rejection_reason"] = _REASON_CAUSALITY_REJECTED
                rejected_frames.append(bad)
                df = df[~bad_causality].copy()

        # ── 7. Drop duplicates ────────────────────────────────────────────
        if cfg.drop_duplicates:
            dupes = df.duplicated(subset=[ec, sc, en], keep="first")
            if dupes.any():
                bad = df[dupes].copy()
                bad["_rejection_reason"] = _REASON_DUPLICATE
                rejected_frames.append(bad)
                df = df[~dupes].copy()

        # ── Combine rejected and modified ─────────────────────────────────
        self._rejected = (
            pd.concat(rejected_frames, ignore_index=True)
            if rejected_frames
            else pd.DataFrame(columns=list(df.columns) + ["_rejection_reason"])
        )
        self._modified = (
            pd.concat(modified_frames, ignore_index=True)
            if modified_frames
            else pd.DataFrame(columns=list(df.columns) + ["_rejection_reason"])
        )

        self._cleaned = df.reset_index(drop=True)

        # ── 8. Merge overlapping ──────────────────────────────────────────
        if cfg.merge_overlapping and len(self._cleaned) > 0:
            self._cleaned = merge_overlapping_events(
                self._cleaned, self._semantics, cfg.meaningful_gap
            )

        return Events(self._cleaned, self._semantics)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def rejected(self) -> pd.DataFrame:
        """Rows that were removed, with _rejection_reason column."""
        self._require_cleaned("rejected")
        return self._rejected.copy()

    @property
    def modified(self) -> pd.DataFrame:
        """Rows that were kept but modified (coalesced or swapped),
        with _rejection_reason describing what changed."""
        self._require_cleaned("modified")
        return self._modified.copy()

    # ------------------------------------------------------------------ #
    # Quality report
    # ------------------------------------------------------------------ #

    def quality_report(self) -> None:
        """Print a structured summary of the cleaning results."""
        self._require_cleaned("quality_report")

        n_clean    = len(self._cleaned)
        n_rejected = len(self._rejected)
        n_modified = len(self._modified)
        n_total    = self._n_input

        print(f"Cleaning report")
        print(f"{'─' * 56}")
        print(f"{'Total input rows:':<42} {n_total:>8,}")
        print(f"{'─' * 56}")

        # Rejected
        if n_rejected > 0:
            print(f"  Rejected:")
            counts = (
                self._rejected["_rejection_reason"]
                .value_counts().reset_index()
            )
            counts.columns = ["reason", "n"]
            for _, row in counts.iterrows():
                label = f"    {row['reason']}:"
                print(f"{label:<44} {int(row['n']):>6,}   ({round(100*row['n']/n_total,1)}%)")
        else:
            print(f"  No rows rejected")

        # Modified
        if n_modified > 0:
            print(f"  Modified (kept):")
            counts = (
                self._modified["_rejection_reason"]
                .value_counts().reset_index()
            )
            counts.columns = ["reason", "n"]
            for _, row in counts.iterrows():
                label = f"    {row['reason']}:"
                print(f"{label:<44} {int(row['n']):>6,}   ({round(100*row['n']/n_total,1)}%)")

        print(f"{'─' * 56}")
        print(f"{'Total rejected:':<42} {n_rejected:>8,}   ({round(100*n_rejected/n_total,1)}%)")
        if n_modified > 0:
            print(f"{'Total modified (kept):':<42} {n_modified:>8,}   ({round(100*n_modified/n_total,1)}%)")
        print(f"{'Clean rows:':<42} {n_clean:>8,}   ({round(100*n_clean/n_total,1)}%)")

        if self._config.merge_overlapping:
            print(f"{'─' * 56}")
            print(f"  Overlapping intervals merged "
                  f"(meaningful_gap={self._config.meaningful_gap} days)")
            print(f"{'Clean rows after merge:':<42} {n_clean:>8,}")

    def quality_report_df(self) -> pd.DataFrame:
        """Return quality report as a DataFrame."""
        self._require_cleaned("quality_report_df")

        n_total = self._n_input
        rows    = []

        for df_, action in [(self._rejected, "rejected"), (self._modified, "modified")]:
            if len(df_) > 0:
                counts = df_["_rejection_reason"].value_counts().reset_index()
                counts.columns = ["reason", "n"]
                counts["action"] = action
                counts["pct_of_input"] = (counts["n"] / n_total * 100).round(1)
                rows.extend(counts.to_dict("records"))

        rows.append({
            "reason":       "CLEAN",
            "n":            len(self._cleaned),
            "action":       "kept",
            "pct_of_input": round(100 * len(self._cleaned) / n_total, 1),
        })

        return pd.DataFrame(rows)[["reason", "action", "n", "pct_of_input"]]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_cleaned(self, method_name: str) -> None:
        if self._cleaned is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires calling .clean() first."
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
