"""
events.py
Events — a boring, validated container for event data.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from semantics.event_semantics import EventSemantics

_ERROR_PREFIX = "[Events] Error"


class Events:
    """
    A validated container for event data.

    Holds a DataFrame of events with start and end times.
    Validates structure at construction — if an Events object exists,
    it is structurally sound. Row-level cleaning is the responsibility
    of EventsCleaner.

    Parameters
    ----------
    data : pd.DataFrame
        Structurally valid event data. No nulls in entity_id,
        start_time, or end_time columns.
    semantics : EventSemantics
        Column mapping for entity_id, start_time, end_time.

    Examples
    --------
    >>> # From clean data
    >>> events = Events(df, sem)

    >>> # From messy data — clean first
    >>> events = EventsCleaner(df, sem, config).clean()
    """

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> None:
        self._validate_semantics(data, semantics)
        self._validate_columns(data, semantics)
        data = self._parse_dates(data, semantics)
        self._validate_no_nulls(data, semantics)

        self.data      = data.copy().reset_index(drop=True)
        self.semantics = semantics

    # ------------------------------------------------------------------ #
    # Structural validation helpers
    # ------------------------------------------------------------------ #

    def _validate_semantics(
        self, data: pd.DataFrame, semantics: EventSemantics
    ) -> None:
        """Raise if data is not a DataFrame or semantics is not EventSemantics."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if not isinstance(semantics, EventSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an EventSemantics object, "
                f"got {type(semantics).__name__}"
            )

    def _validate_columns(
        self, data: pd.DataFrame, sem: EventSemantics
    ) -> None:
        """Raise if any required columns are missing."""
        required = [sem.entity_id_col, sem.start_time_col, sem.end_time_col]
        if sem.event_id_col:   required.append(sem.event_id_col)
        if sem.event_type_col: required.append(sem.event_type_col)
        required.extend(sem.metadata_cols)
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: missing required columns: {missing}"
            )

    def _parse_dates(
        self, data: pd.DataFrame, sem: EventSemantics
    ) -> pd.DataFrame:
        """Parse start and end columns to datetime. Returns modified DataFrame."""
        data = data.copy()
        for col in [sem.start_time_col, sem.end_time_col]:
            data[col] = pd.to_datetime(data[col], errors="coerce")
        return data

    def _validate_no_nulls(
        self, data: pd.DataFrame, sem: EventSemantics
    ) -> None:
        """Raise if any required column has null values."""
        cols = [sem.entity_id_col, sem.start_time_col, sem.end_time_col]
        bad  = {
            col: int(data[col].isna().sum())
            for col in cols
            if data[col].isna().any()
        }
        if bad:
            details = ", ".join(
                f"'{col}': {n} null(s)" for col, n in bad.items()
            )
            raise ValueError(
                f"{_ERROR_PREFIX}: data contains null values in required "
                f"columns — {details}. "
                f"Use EventsCleaner to handle these before constructing Events."
            )

    # ------------------------------------------------------------------ #
    # Class methods
    # ------------------------------------------------------------------ #

    @classmethod
    def _build_from_cleaned(cls, data: pd.DataFrame, semantics: EventSemantics) -> "Events":
        """
        Bypass validation to construct an Events from already-clean data.
        Only used internally — never call this on unvalidated data.
        """
        obj           = object.__new__(cls)
        obj.data      = data.copy().reset_index(drop=True)
        obj.semantics = semantics
        return obj

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def filter_by_entities(self, entity_ids: np.ndarray | pd.Series) -> "Events":
        """Return a new Events containing only the specified entities."""
        if not isinstance(entity_ids, (np.ndarray, pd.Series)):
            raise TypeError(
                f"{_ERROR_PREFIX} in filter_by_entities(): entity_ids must be "
                f"a numpy array or pd.Series, got {type(entity_ids).__name__}"
            )
        col      = self.semantics.entity_id_col
        filtered = self.data.loc[self.data[col].isin(entity_ids)].copy()
        return Events._build_from_cleaned(filtered, self.semantics)

    def filter_by_dates(self, start=None, end=None) -> "Events":
        """
        Return a new Events filtered to the given date range.

        Keeps events whose start is >= start AND whose end is <= end.
        Either bound may be omitted.

        Parameters
        ----------
        start : str | pd.Timestamp | None
            Lower bound — keep events starting on or after this date.
        end : str | pd.Timestamp | None
            Upper bound — keep events ending on or before this date.
        """
        if start is None and end is None:
            raise ValueError(
                f"{_ERROR_PREFIX} in filter_by_dates(): "
                f"at least one of start or end must be provided."
            )

        if start is not None:
            try:
                start = pd.Timestamp(start)
            except Exception:
                raise ValueError(
                    f"{_ERROR_PREFIX} in filter_by_dates(): "
                    f"start={start!r} could not be parsed as a date."
                )

        if end is not None:
            try:
                end = pd.Timestamp(end)
            except Exception:
                raise ValueError(
                    f"{_ERROR_PREFIX} in filter_by_dates(): "
                    f"end={end!r} could not be parsed as a date."
                )

        if start is not None and end is not None and start > end:
            raise ValueError(
                f"{_ERROR_PREFIX} in filter_by_dates(): "
                f"start ({start.date()}) must be before end ({end.date()})."
            )

        sc = self.semantics.start_time_col
        ec = self.semantics.end_time_col
        df = self.data

        if start is not None:
            df = df[df[sc] >= start]
        if end is not None:
            df = df[df[ec] <= end]

        return Events._build_from_cleaned(df.copy(), self.semantics)

    def copy(self) -> "Events":
        """Return a copy of this Events object."""
        return Events._build_from_cleaned(self.data.copy(), self.semantics)

    def build_summary(self) -> dict:  
        """Return a summary of this Events object as a dictionary."""  
        sc  = self.semantics.start_time_col  
        ec  = self.semantics.end_time_col  
        eid = self.semantics.entity_id_col  
    
        n_rows     = len(self.data)  
        n_entities = self.data[eid].nunique()  
        date_min   = self.data[sc].min().date()  
        date_max   = self.data[ec].max().date()  
        durations  = (self.data[ec] - self.data[sc]).dt.days  
        avg_dur    = round(durations.mean(), 1)  
        min_dur    = int(durations.min())  
        max_dur    = int(durations.max())  
    
        summary = {  
            "total_rows": n_rows,  
            "unique_entities": n_entities,  
            "date_range": (str(date_min), str(date_max)),  
            "avg_duration_days": avg_dur,  
            "min_duration_days": min_dur,  
            "max_duration_days": max_dur,  
        }  
    
        return summary  

    def print_summary(self):
        summary = self.build_summary()
        for key, value in summary.items():  
            print(f"{key}: {value}")  
    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (
            f"Events(\n"
            f"  rows             : {len(self):,}\n"
            f"  unique entities  : {self.data[self.semantics.entity_id_col].nunique():,}\n"
            f"  entity_col       : '{self.semantics.entity_id_col}'\n"
            f"  start_col        : '{self.semantics.start_time_col}'\n"
            f"  end_col          : '{self.semantics.end_time_col}'\n"
            f")"
        )