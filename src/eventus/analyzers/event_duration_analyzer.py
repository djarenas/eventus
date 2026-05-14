"""
event_duration_analyzer.py
EventDurationAnalyzer — computes event durations from a validated
Events object and produces an EventDurationResult.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.events import Events

_ERROR_PREFIX = "[EventDurationAnalyzer] Error"


class EventDurationAnalyzer:
    """
    Computes event durations from a validated Events object.

    Each row in the result represents one event with its duration in days.
    Optional descriptor columns from Events.data are carried through to
    the result — these may have nulls, which is by design.

    Parameters
    ----------
    events : Events
        A validated Events object. Must be structurally sound —
        use EventsCleaner first if your data is messy.
    descriptor_cols : list[str] | str | None
        Columns in events.data to carry through to the result as
        per-event descriptors (e.g. "bmi_at_admission", "hospital_id").
        Pass "all" to carry every column beyond the required three.
        Pass a list to be explicit. Default None — lean output only.
        Nulls in descriptor columns are allowed.

    Examples
    --------
    >>> # Plain durations — lean output
    >>> analyzer = EventDurationAnalyzer(events)
    >>> result   = analyzer.calc()

    >>> # With descriptors — explicit
    >>> analyzer = EventDurationAnalyzer(
    ...     events,
    ...     descriptor_cols=["bmi_at_admission", "hospital_id"],
    ... )
    >>> result = analyzer.calc()

    >>> # With descriptors — carry everything
    >>> analyzer = EventDurationAnalyzer(events, descriptor_cols="all")
    >>> result   = analyzer.calc()
    """

    def __init__(
        self,
        events:          Events,
        descriptor_cols: list[str] | str | None = None,
    ) -> None:
        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR_PREFIX}: events must be an Events object, "
                f"got {type(events).__name__}"
            )

        # ── Resolve descriptor_cols ───────────────────────────────────
        resolved = self._resolve_descriptor_cols(
            descriptor_cols, events
        )

        self._events          = events
        self._descriptor_cols = resolved
        self._result          = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def calc(self) -> "EventDurationResult":
        """
        Compute durations and return an EventDurationResult.

        Returns
        -------
        EventDurationResult
            One row per event. Always contains entity_col and
            duration_days. Contains descriptor columns if specified.
        """
        from eventus.intermediates.event_duration_result import EventDurationResult
        from .events_duration_utils import compute_durations

        df = compute_durations(
            data            = self._events.data,
            entity_col      = self._events.semantics.entity_id_col,
            start_col       = self._events.semantics.start_time_col,
            end_col         = self._events.semantics.end_time_col,
            identity        = self._events.semantics.identity,
            descriptor_cols = self._descriptor_cols,
        )

        self._result = EventDurationResult(
            data            = df,
            entity_col      = self._events.semantics.entity_id_col,
            identity        = self._events.semantics.identity,
            descriptor_cols = self._descriptor_cols,
        )
        return self._result

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _resolve_descriptor_cols(
        self,
        descriptor_cols: list[str] | str | None,
        events:          Events,
    ) -> list[str]:
        """
        Resolve descriptor_cols to a validated list of column names.

        "all"  → every column in events.data beyond the required three
        list   → validated explicitly against events.data
        None   → empty list
        """
        core_cols = {
            events.semantics.entity_id_col,
            events.semantics.start_time_col,
            events.semantics.end_time_col,
        }

        if descriptor_cols is None:
            return []

        if descriptor_cols == "all":
            return [
                c for c in events.data.columns
                if c not in core_cols
            ]

        if isinstance(descriptor_cols, str):
            # single string that isn't "all"
            descriptor_cols = [descriptor_cols]

        if not isinstance(descriptor_cols, list):
            raise TypeError(
                f"{_ERROR_PREFIX}: descriptor_cols must be a list, "
                f"'all', or None, got {type(descriptor_cols).__name__}"
            )

        # Validate all specified columns exist
        missing = [
            c for c in descriptor_cols
            if c not in events.data.columns
        ]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: descriptor_cols not found in "
                f"Events.data: {missing}. "
                f"Available columns: {sorted(events.data.columns.tolist())}"
            )

        # Warn if any core columns were accidentally included
        overlap = [c for c in descriptor_cols if c in core_cols]
        if overlap:
            import warnings
            warnings.warn(
                f"[EventDurationAnalyzer] descriptor_cols includes core "
                f"column(s) {overlap} — they will be ignored since they "
                f"are already present in the result.",
                UserWarning,
                stacklevel=3,
            )
            descriptor_cols = [c for c in descriptor_cols if c not in core_cols]

        return list(descriptor_cols)

    def _require_calc(self, method_name: str) -> None:
        if self._result is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires calling "
                f".calc() first."
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        sid    = self._events.semantics.identity
        status = "calculated" if self._result is not None else "not yet calculated"
        desc   = self._descriptor_cols if self._descriptor_cols else "none"
        return (
            f"EventDurationAnalyzer(\n"
            f"  identity        : {sid!r}\n"
            f"  events          : {len(self._events):,} rows\n"
            f"  descriptor_cols : {desc}\n"
            f"  status          : {status}\n"
            f")"
        )
