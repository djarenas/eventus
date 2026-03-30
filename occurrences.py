"""
occurrences.py
A validated collection of point-in-time occurrences (no end date).
Mirrors the Events pattern — validates inputs and triages bad rows.
"""
from __future__ import annotations
import pandas as pd
from .occurrence_semantics import OccurrenceSemantics

_ERROR_PREFIX = "[Occurrences] Error"


class Occurrences:
    """
    A validated collection of point-in-time occurrences.

    Each occurrence has an entity and a date. Unlike Events, there is
    no end date — occurrences are instantaneous.

    Bad rows (null entity or unparseable date) are triaged into .rejected.
    Everything in .data is guaranteed structurally valid.

    No validation is performed on date ranges — use filter_by_dates()
    to restrict to a meaningful window.

    Attributes
    ----------
    data : pd.DataFrame
        Valid occurrences only.
    semantics : OccurrenceSemantics
        Column mappings.
    rejected : pd.DataFrame
        Rows with bad data, includes '_rejection_reason' column.
    """

    _ERROR_PREFIX = "[Occurrences] Error"

    def __init__(self, data_input: pd.DataFrame, semantics: OccurrenceSemantics) -> None:
        data = data_input.copy()
        self._validate_input(data, semantics)
        self._validate_columns_exist(data, semantics)
        data = self._ensure_date_type(data, semantics)
        self.semantics = semantics
        self.data, self.rejected = self._triage(data)
        self._report_rejected()

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def copy(self) -> "Occurrences":
        return Occurrences(self.data.copy(), self.semantics)

    def filter_by_entities(self, entity_ids: list) -> "Occurrences":
        """Return a new Occurrences keeping only the given entities."""
        col = self.semantics.entity_id_col
        filtered = self.data[self.data[col].isin(entity_ids)]
        return Occurrences(filtered, self.semantics)

    def filter_by_dates(self, start=None, end=None) -> "Occurrences":
        """
        Return a new Occurrences keeping only occurrences within [start, end].
        start and end are inclusive. Pass None to leave unbounded.
        """
        col = self.semantics.date_col
        filtered = self.data
        if start is not None:
            filtered = filtered[filtered[col] >= pd.Timestamp(start)]
        if end is not None:
            filtered = filtered[filtered[col] <= pd.Timestamp(end)]
        return Occurrences(filtered, self.semantics)

    def count_per_entity(self) -> pd.Series:
        """Return a Series of occurrence counts indexed by entity_id."""
        return self.data.groupby(self.semantics.entity_id_col).size()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _validate_input(self, data: pd.DataFrame, semantics: OccurrenceSemantics) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{self._ERROR_PREFIX}: data must be a pandas DataFrame"
            )
        if not isinstance(semantics, OccurrenceSemantics):
            raise TypeError(
                f"{self._ERROR_PREFIX}: semantics must be an OccurrenceSemantics object"
            )

    def _validate_columns_exist(self, data: pd.DataFrame, semantics: OccurrenceSemantics) -> None:
        required = [semantics.entity_id_col, semantics.date_col]
        if semantics.occurrence_id_col:
            required.append(semantics.occurrence_id_col)
        required.extend(semantics.metadata_cols)
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(
                f"{self._ERROR_PREFIX}: missing columns in DataFrame: {missing}"
            )

    def _ensure_date_type(self, data: pd.DataFrame, semantics: OccurrenceSemantics) -> pd.DataFrame:
        data[semantics.date_col] = pd.to_datetime(data[semantics.date_col], errors="coerce")
        return data

    def _triage(self, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Separate valid rows from bad rows, tagging rejection reasons."""
        reasons = pd.Series("", index=data.index)

        # Null entity
        null_entity = data[self.semantics.entity_id_col].isna()
        reasons[null_entity] += f"null_{self.semantics.entity_id_col}; "

        # Null or unparseable date (coerced to NaT above)
        null_date = data[self.semantics.date_col].isna()
        reasons[null_date] += f"null_or_invalid_{self.semantics.date_col}; "

        is_rejected = reasons.str.len() > 0
        rejected = data[is_rejected].copy()
        rejected["_rejection_reason"] = reasons[is_rejected].str.rstrip("; ")
        good = data[~is_rejected].copy()

        return good, rejected

    def _report_rejected(self) -> None:
        if len(self.rejected) == 0:
            return
        total = len(self.data) + len(self.rejected)
        print(
            f"Warning: {len(self.rejected)}/{total} rows rejected. "
            f"Reasons: {self.rejected['_rejection_reason'].value_counts().to_dict()}"
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        identity = f" ({self.semantics.identity})" if self.semantics.identity else ""
        return (
            f"Occurrences{identity}("
            f"{len(self)} rows, "
            f"entity_col='{self.semantics.entity_id_col}', "
            f"date_col='{self.semantics.date_col}')"
        )
