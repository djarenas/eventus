"""
occurrences_cleaner.py
OccurrencesCleaner — transparent, auditable cleaning of raw occurrence data.
Produces a validated Occurrences object with a full quality report.
"""
from __future__ import annotations
import pandas as pd

from eventus.semantics.occurrence_semantics import OccurrenceSemantics
from .occurrences_cleaner_config import OccurrencesCleanerConfig

_ERROR_PREFIX = "[OccurrencesCleaner] Error"

# Rejection reasons
_REASON_NULL_ENTITY    = "null_entity_id"
_REASON_NULL_DATE      = "null_date"
_REASON_PARSE_DATE     = "unparseable_date"
_REASON_BEFORE_FLOOR   = "before_date_floor"
_REASON_AFTER_CEILING  = "after_date_ceiling"
_REASON_DUPLICATE      = "duplicate_row"


class OccurrencesCleaner:
    """
    'I am a transparent, auditable pipeline that cleans raw occurrence data and records every decision I make.'

    Applies configurable cleaning rules to a raw DataFrame and produces
    a validated Occurrences object. Every rejected row is recorded with
    an explicit reason. Call print_quality_report() to see a full
    summary of what happened and why.

    Parameters
    ----------
    data : pd.DataFrame
        Raw input DataFrame — may be messy.
    semantics : OccurrenceSemantics
        Column mapping for entity_id and date.
    config : OccurrencesCleanerConfig | None
        Cleaning rules. Defaults to OccurrencesCleanerConfig() if None.

    Examples
    --------
    >>> cleaner = OccurrencesCleaner(raw_df, sem)
    >>> occs    = cleaner.clean()
    >>> cleaner.print_quality_report()

    >>> config  = OccurrencesCleanerConfig.build_from_yaml("cleaner.yaml")
    >>> cleaner = OccurrencesCleaner(raw_df, sem, config)
    >>> occs    = cleaner.clean()
    """

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
        config:    OccurrencesCleanerConfig | None = None,
    ) -> None:
        if not isinstance(semantics, OccurrenceSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an OccurrenceSemantics "
                f"object, got {type(semantics).__name__}"
            )
        if config is None:
            config = OccurrencesCleanerConfig()
        if not isinstance(config, OccurrencesCleanerConfig):
            raise TypeError(
                f"{_ERROR_PREFIX}: config must be an OccurrencesCleanerConfig "
                f"object, got {type(config).__name__}"
            )

        self._raw       = data.copy()
        self._semantics = semantics
        self._config    = config
        self._cleaned   = None
        self._rejected  = None
        self._n_input   = len(data)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def clean(self) -> "Occurrences":
        """
        Apply cleaning rules and return a validated Occurrences object.

        Pipeline order:
        1.  Parse dates             (if config.parse_dates)
        2.  Normalize to date only  (if config.normalize_dates)
        3.  Reject null entity IDs
        4.  Reject null or unparseable dates
        5.  Reject rows outside date_floor / date_ceiling
        6.  Drop exact duplicates   (if config.drop_duplicates)

        Returns
        -------
        Occurrences
            A validated Occurrences object containing only clean rows.
        """
        from eventus.data_objects.occurrences import Occurrences

        df  = self._raw.copy()
        ec  = self._semantics.entity_id_col
        dc  = self._semantics.date_col
        cfg = self._config

        rejected_frames = []

        # ── 1. Parse dates ────────────────────────────────────────────────
        if dc not in df.columns:
            raise ValueError(
                f"{_ERROR_PREFIX}: date column '{dc}' not found in data. "
                f"Available: {sorted(df.columns.tolist())}"
            )
        if ec not in df.columns:
            raise ValueError(
                f"{_ERROR_PREFIX}: entity column '{ec}' not found in data. "
                f"Available: {sorted(df.columns.tolist())}"
            )

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

        # ── 6. Drop duplicates ────────────────────────────────────────────
        if cfg.drop_duplicates:
            dupes = df.duplicated(subset=[ec, dc], keep="first")
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

        return Occurrences.construct_from_clean(self._cleaned, self._semantics)

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
        self._require_cleaned("print_quality_report")

        n_clean    = len(self._cleaned)
        n_rejected = len(self._rejected)
        n_total    = self._n_input

        print(f"Cleaning report — occurrences")
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
        print(
            f"{'Clean rows:':<42} {n_clean:>8,}"
            f"   ({round(100 * n_clean / n_total, 1)}%)"
        )

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
            counts["pct_of_input"] = (
                counts["n"] / n_total * 100
            ).round(1)
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
                f"{_ERROR_PREFIX}: .{method_name}() requires calling "
                f".clean() first."
            )

    def __repr__(self) -> str:
        status = "cleaned" if self._cleaned is not None else "not yet cleaned"
        return (
            f"OccurrencesCleaner(\n"
            f"  input rows : {self._n_input:,}\n"
            f"  status     : {status}\n"
            f"  config     : {self._config.__class__.__name__}\n"
            f")"
        )
