"""
events.py
Events — a validated collection of point-in-time events.

Events are instantaneous episodes — they have an entity and a date
but no end date. Unlike Episodes, there is no duration, no causality
check, and no overlap merging.

If it exists, it is complete. The constructor raises on invalid data.
Row-level cleaning is the responsibility of EventsCleaner.
"""
from __future__ import annotations
import pandas as pd

from eventus.semantics.event_semantics import EventSemantics



_ERROR_PREFIX = "[Events] Error"

class Events:
    """
    A validated collection of point-in-time events.

    Each event has an entity identifier and a date.
    Unlike Episodes, there is no end date — events are instantaneous.

    The constructor raises on any invalid data — null entity IDs,
    null or unparseable dates. Use EventsCleaner to handle
    messy raw data before constructing this object.

    Attributes
    ----------
    data : pd.DataFrame
        Validated events. Dates are normalized (time component removed).
    semantics : EventSemantics
        Column mappings and identity label.

    Examples
    --------
    >>> sem  = EventSemantics(
    ...     entity_id_col = "patient_id",
    ...     date_col      = "ed_visit_date",
    ...     identity      = "ed_visit",
    ... )
    >>> occs = Events(df, sem)
    >>> occs.print_summary()
    """

    # ── Attributes ───────────────────────────────────────────────────────
    data:      pd.DataFrame    # validated event rows, dates normalized
    semantics: EventSemantics  # column mappings and identity label

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> None:
        self._validate_semantics(semantics)
        data = data.copy()
        self._validate_columns(data, semantics)
        data = self._parse_date(data, semantics)
        self._validate_no_nulls(data, semantics)
        self.data      = data.reset_index(drop=True)
        self.semantics = semantics

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def copy(self) -> "Events":
        """Return a copy of this Events."""
        return Events._construct_from_cleaned(self.data.copy(), self.semantics)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def _construct_from_cleaned(
        cls,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> "Events":
        """
        Construct an Events from already-validated data,
        bypassing validation. Used by filter methods and copy().
        """
        obj           = object.__new__(cls)
        obj.data      = data.reset_index(drop=True)
        obj.semantics = semantics
        return obj

    def _validate_semantics(self, semantics: EventSemantics) -> None:
        if not isinstance(semantics, EventSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an EventSemantics "
                f"object, got {type(semantics).__name__}"
            )

    def _validate_columns(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        required = [semantics.entity_id_col, semantics.date_col]
        if semantics.event_id_col:
            required.append(semantics.event_id_col)
        required.extend(semantics.metadata_cols)
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: missing required columns: {missing}. "
                f"Available: {sorted(data.columns.tolist())}"
            )

    def _parse_date(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> pd.DataFrame:
        """Parse and normalize the date column."""
        col         = semantics.date_col
        data[col]   = pd.to_datetime(data[col], errors="coerce")
        data[col]   = data[col].dt.normalize()
        return data

    def _validate_no_nulls(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
    ) -> None:
        """Raise if any entity IDs or dates are null."""
        entity_col = semantics.entity_id_col
        date_col   = semantics.date_col

        # Null entity IDs
        null_entity = data[entity_col].isna()
        if null_entity.any():
            n       = null_entity.sum()
            raise ValueError(
                f"{_ERROR_PREFIX}: '{entity_col}' contains {n:,} null "
                f"value(s). Use EventsCleaner to remove these "
                f"before constructing Events."
            )

        # Null or unparseable dates
        null_date = data[date_col].isna()
        if null_date.any():
            n        = null_date.sum()
            examples = data.loc[null_date, entity_col].head(3).tolist()
            raise ValueError(
                f"{_ERROR_PREFIX}: '{date_col}' contains {n:,} null or "
                f"unparseable value(s). "
                f"Example entity IDs: {examples}. "
                f"Use EventsCleaner to handle these before "
                f"constructing Events."
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (
            f"Events(\n"
            f"  identity        : {self.semantics.identity!r}\n"
            f"  rows            : {len(self):,}\n"
            f"  unique entities : {self.data[self.semantics.entity_id_col].nunique():,}\n"
            f"  entity_col      : '{self.semantics.entity_id_col}'\n"
            f"  date_col        : '{self.semantics.date_col}'\n"
            f")"
        )
