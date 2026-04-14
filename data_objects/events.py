"""
events.py
Events — a boring, validated container for event data.
"""
from __future__ import annotations
import sys
import pandas as pd

sys.path.append("C:/Users/DanielArenas/Desktop/Github_Local/Python_Events_Classes")
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
    # Public methods
    # ------------------------------------------------------------------ #

    def filter_by_entities(self, entity_ids) -> "Events":
        """Return a new Events containing only the specified entities."""
        col = self.semantics.entity_id_col
        return Events(
            self.data[self.data[col].isin(entity_ids)].copy(),
            self.semantics
        )

    def filter_by_dates(self, start=None, end=None) -> "Events":
        """Return a new Events filtered to the given date range."""
        f = self.data
        sc = self.semantics.start_time_col
        ec = self.semantics.end_time_col
        if start is not None:
            f = f[f[sc] >= pd.Timestamp(start)]
        if end is not None:
            f = f[f[ec] <= pd.Timestamp(end)]
        return Events(f.copy(), self.semantics)

    def copy(self) -> "Events":
        """Return a copy of this Events object."""
        return Events(self.data.copy(), self.semantics)

    def summary(self) -> None:
        """Print a human-readable summary of this Events object."""
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

        print(f"Events summary")
        print(f"{'─' * 42}")
        print(f"{'Total rows':<25}: {n_rows:>10,}")
        print(f"{'Unique entities':<25}: {n_entities:>10,}")
        print(f"{'Date range':<25}: {date_min}  →  {date_max}")
        print(f"{'Avg duration':<25}: {avg_dur:>10.1f} days")
        print(f"{'Min duration':<25}: {min_dur:>10} days")
        print(f"{'Max duration':<25}: {max_dur:>10} days")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (
            f"Events(\n"
            f"  rows       : {len(self):,}\n"
            f"  entity_col : '{self.semantics.entity_id_col}'\n"
            f"  start_col  : '{self.semantics.start_time_col}'\n"
            f"  end_col    : '{self.semantics.end_time_col}'\n"
            f")"
        )