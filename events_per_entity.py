"""
events_per_entity.py
A specialized Events subclass that enforces one row per entity.
"""
from __future__ import annotations
import pandas as pd
from .events import Events
from .event_semantics import EventSemantics


class EventsPerEntity(Events):
    """
    An Events collection where each entity appears exactly once.

    Inherits all validation, triage, and functionality from Events.
    Adds one additional constraint: entity_id_col must be unique
    across all rows in .data after triage.

    Useful for span data, membership tables, or any dataset where
    one row per entity is a structural requirement.

    Raises
    ------
    ValueError
        If any entity appears more than once in the valid data.
    """

    _ERROR_PREFIX = "[EventsPerEntity] Error"

    def __init__(self, data_input: pd.DataFrame, semantics: EventSemantics):
        super().__init__(data_input, semantics)
        self._validate_one_row_per_entity()

    def _validate_one_row_per_entity(self) -> None:
        """Raise if any entity appears more than once in .data."""
        col = self.semantics.entity_id_col
        duplicated = self.data[self.data[col].duplicated(keep=False)]
        if not duplicated.empty:
            dupes = duplicated[col].unique().tolist()
            raise ValueError(
                f"{self._ERROR_PREFIX}: entity_id_col '{col}' must be unique "
                f"across all rows. Duplicate entities found: {dupes}"
            )

    def __repr__(self) -> str:
        return (
            f"EventsPerEntity({len(self)} rows, "
            f"entity_col='{self.semantics.entity_id_col}')"
        )
