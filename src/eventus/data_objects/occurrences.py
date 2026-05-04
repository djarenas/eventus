"""
occurrences.py
Occurrences — a validated collection of point-in-time occurrences.

Occurrences are instantaneous events — they have an entity and a date
but no end date. Unlike Events, there is no duration, no causality
check, and no overlap merging.

If it exists, it is complete. The constructor raises on invalid data.
Row-level cleaning is the responsibility of OccurrencesCleaner.
"""
from __future__ import annotations
import warnings
import pandas as pd

from eventus.semantics.occurrence_semantics import OccurrenceSemantics



_ERROR_PREFIX = "[Occurrences] Error"

class Occurrences:
    """
    A validated collection of point-in-time occurrences.

    Each occurrence has an entity identifier and a date.
    Unlike Events, there is no end date — occurrences are instantaneous.

    The constructor raises on any invalid data — null entity IDs,
    null or unparseable dates. Use OccurrencesCleaner to handle
    messy raw data before constructing this object.

    Attributes
    ----------
    data : pd.DataFrame
        Validated occurrences. Dates are normalized (time component removed).
    semantics : OccurrenceSemantics
        Column mappings and identity label.

    Examples
    --------
    >>> sem  = OccurrenceSemantics(
    ...     entity_id_col = "patient_id",
    ...     date_col      = "ed_visit_date",
    ...     identity      = "ed_visit",
    ... )
    >>> occs = Occurrences(df, sem)
    >>> occs.print_summary()
    """

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
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

    def filter_by_entities(self, entity_ids) -> "Occurrences":
        """
        Return a new Occurrences containing only the specified entities.

        Parameters
        ----------
        entity_ids : list or set
            Entity identifiers to keep.
        """
        col      = self.semantics.entity_id_col
        filtered = self.data[self.data[col].isin(entity_ids)].copy()
        return Occurrences.construct_from_clean(filtered, self.semantics)

    def filter_by_dates(
        self,
        start = None,
        end   = None,
    ) -> "Occurrences":
        """
        Return a new Occurrences keeping only occurrences within [start, end].
        Both bounds are inclusive. Pass None to leave unbounded.

        Parameters
        ----------
        start : str | pd.Timestamp | None
            Lower bound (inclusive).
        end : str | pd.Timestamp | None
            Upper bound (inclusive).
        """
        col      = self.semantics.date_col
        filtered = self.data.copy()
        if start is not None:
            filtered = filtered[filtered[col] >= pd.Timestamp(start)]
        if end is not None:
            filtered = filtered[filtered[col] <= pd.Timestamp(end)]
        return Occurrences.construct_from_clean(filtered, self.semantics)

    def count_per_entity(self) -> pd.Series:
        """
        Return occurrence counts indexed by entity ID.

        Returns
        -------
        pd.Series
            Index: entity_id_col values. Values: occurrence counts.
        """
        return self.data.groupby(self.semantics.entity_id_col).size()

    def copy(self) -> "Occurrences":
        """Return a copy of this Occurrences."""
        return Occurrences.construct_from_clean(self.data.copy(), self.semantics)


    def build_summary(self) -> dict:  
        """Return a structured summary of occurrences as a dictionary."""  
        col        = self.semantics.date_col  
        entity_col = self.semantics.entity_id_col  
        identity   = self.semantics.identity or "—"  
    
        counts = self.count_per_entity()  
    
        summary = {  
            "identity": identity,  
            "total_rows": len(self.data),  
            "unique_entities": self.data[entity_col].nunique(),  
            "earliest_date": str(self.data[col].min().date()),  
            "latest_date": str(self.data[col].max().date()),  
            "mean_per_entity": round(counts.mean(), 1),  
            "max_per_entity": int(counts.max())  
        }  
    
        return summary  

    def print_summary(self):
        summary = self.build_summary()
        for key, value in summary.items():  
            print(f"{key}: {value}")  

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def construct_from_clean(
        cls,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
    ) -> "Occurrences":
        """
        Construct an Occurrences from already-validated data,
        bypassing validation. Used by filter methods and copy().
        """
        obj           = object.__new__(cls)
        obj.data      = data.reset_index(drop=True)
        obj.semantics = semantics
        return obj

    def _validate_semantics(self, semantics: OccurrenceSemantics) -> None:
        if not isinstance(semantics, OccurrenceSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an OccurrenceSemantics "
                f"object, got {type(semantics).__name__}"
            )

    def _validate_columns(
        self,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
    ) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        required = [semantics.entity_id_col, semantics.date_col]
        if semantics.occurrence_id_col:
            required.append(semantics.occurrence_id_col)
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
        semantics: OccurrenceSemantics,
    ) -> pd.DataFrame:
        """Parse and normalize the date column."""
        col         = semantics.date_col
        data[col]   = pd.to_datetime(data[col], errors="coerce")
        data[col]   = data[col].dt.normalize()
        return data

    def _validate_no_nulls(
        self,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
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
                f"value(s). Use OccurrencesCleaner to remove these "
                f"before constructing Occurrences."
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
                f"Use OccurrencesCleaner to handle these before "
                f"constructing Occurrences."
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (
            f"Occurrences(\n"
            f"  identity        : {self.semantics.identity!r}\n"
            f"  rows            : {len(self):,}\n"
            f"  unique entities : {self.data[self.semantics.entity_id_col].nunique():,}\n"
            f"  entity_col      : '{self.semantics.entity_id_col}'\n"
            f"  date_col        : '{self.semantics.date_col}'\n"
            f")"
        )
