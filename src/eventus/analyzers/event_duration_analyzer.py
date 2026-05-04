"""
event_duration_analyzer.py
EventDurationAnalyzer — computes event durations from a validated Events object.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.events import Events

_ERROR_PREFIX = "[EventDurationAnalyzer] Error"


class EventDurationAnalyzer:
    """
    Computes event durations from a validated Events object.

    Each row in the output represents one event with its duration in days.
    Optional stratification groups events by a metadata column already
    present in Events.data — no separate lookup needed.

    Parameters
    ----------
    events : Events
        A validated Events object. Must be structurally sound —
        use EventsCleaner first if your data is messy.
    stratify_by : str | None
        Column in events.data to stratify by. Must exist. Nulls
        are filled with 'missing'. Max 10 unique categories.
        Default None — no stratification.
    max_categories : int
        Maximum unique categories allowed in stratify_by.
        Default 10. Raise an error if exceeded — come on bro.

    Examples
    --------
    >>> # Plain durations
    >>> analyzer = EventDurationAnalyzer(events)
    >>> df = analyzer.calc()
    >>> df.head()

    >>> # Stratified by hospital
    >>> analyzer = EventDurationAnalyzer(events, stratify_by="hospital_id")
    >>> df = analyzer.calc()
    """

    def __init__(
        self,
        events:         Events,
        stratify_by:    str | None = None,
        max_categories: int        = 10,
    ) -> None:
        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR_PREFIX}: events must be an Events object, "
                f"got {type(events).__name__}"
            )
        if stratify_by is not None and not isinstance(stratify_by, str):
            raise TypeError(
                f"{_ERROR_PREFIX}: stratify_by must be a string or None, "
                f"got {type(stratify_by).__name__}"
            )
        if not isinstance(max_categories, int) or max_categories < 2:
            raise ValueError(
                f"{_ERROR_PREFIX}: max_categories must be an integer >= 2, "
                f"got {max_categories!r}"
            )

        self._events         = events
        self._stratify_by    = stratify_by
        self._max_categories = max_categories
        self._result         = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def calc(self) -> pd.DataFrame:
        """
        Compute durations and return a DataFrame.

        Runs validation, computes duration_days for each event,
        optionally adds stratify_col.

        Returns
        -------
        pd.DataFrame
            Columns:
            - entity_col (from semantics)
            - duration_days
            - identity (if EventSemantics.identity is set)
            - stratify_col (if stratify_by is set)
        """
        from .events_duration_utils import compute_durations

        self._result = compute_durations(
            data           = self._events.data,
            entity_col     = self._events.semantics.entity_id_col,
            start_col      = self._events.semantics.start_time_col,
            end_col        = self._events.semantics.end_time_col,
            identity       = self._events.semantics.identity,
            stratify_by    = self._stratify_by,
            max_categories = self._max_categories,
        )
        return self._result.copy()

    def summary(self) -> None:
        """Print a summary of the duration analysis. Requires calc() first."""
        self._require_calc("summary")

        df  = self._result
        ec  = self._events.semantics.entity_id_col
        sid = self._events.semantics.identity

        print(f"EventDurationAnalyzer summary")
        if sid:
            print(f"  identity     : {sid}")
        print(f"{'─' * 46}")
        print(f"{'Total events':<30}: {len(df):>10,}")
        print(f"{'Unique entities':<30}: {df[ec].nunique():>10,}")
        print(f"{'Mean duration':<30}: {df['duration_days'].mean():>10.1f} days")
        print(f"{'Median duration':<30}: {df['duration_days'].median():>10.1f} days")
        print(f"{'Min duration':<30}: {df['duration_days'].min():>10} days")
        print(f"{'Max duration':<30}: {df['duration_days'].max():>10} days")

        if "stratify_col" in df.columns:
            print(f"{'─' * 46}")
            print(f"  Stratified by: '{self._stratify_by}'")
            cats = df.groupby("stratify_col")["duration_days"]
            for cat, grp in cats:
                print(f"    {cat:<20}: n={len(grp):,}  "
                      f"mean={grp.mean():.1f}d  "
                      f"median={grp.median():.1f}d")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_calc(self, method_name: str) -> None:
        if self._result is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires calling "
                f".calc() first."
            )

    def __repr__(self) -> str:
        sid    = self._events.semantics.identity
        status = "calculated" if self._result is not None else "not yet calculated"
        return (
            f"EventDurationAnalyzer(\n"
            f"  identity       : {sid!r}\n"
            f"  events         : {len(self._events):,} rows\n"
            f"  stratify_by    : {self._stratify_by!r}\n"
            f"  max_categories : {self._max_categories}\n"
            f"  status         : {status}\n"
            f")"
        )
