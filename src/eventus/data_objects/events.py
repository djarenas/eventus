"""
events.py
Events — a boring, but validated, container for event data.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from eventus.semantics.event_semantics import EventSemantics

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
        self._validate_causality(data, semantics)

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

    def _validate_causality(
        self, data: pd.DataFrame, sem: EventSemantics
    ) -> None:
        """Raise if any event has start strictly after end."""
        sc  = sem.start_time_col
        ec  = sem.end_time_col
        bad = data[data[sc] > data[ec]]
        if not bad.empty:
            n        = len(bad)
            examples = (
                bad[[sem.entity_id_col, sc, ec]]
                .head(3)
                .to_dict("records")
            )
            raise ValueError(
                f"{_ERROR_PREFIX}: {n:,} row(s) violate causality — "
                f"start must be before or equal to end. "
                f"Examples: {examples}. "
                f"Use EventsCleaner to swap or remove these rows before "
                f"constructing Events."
            )

    # ------------------------------------------------------------------ #
    # Class methods
    # ------------------------------------------------------------------ #

    @classmethod
    def _construct_from_cleaned(cls, data: pd.DataFrame, semantics: EventSemantics) -> "Events":
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

    def copy(self) -> "Events":
        """Return a copy of this Events object."""
        return Events._construct_from_cleaned(self.data.copy(), self.semantics)

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