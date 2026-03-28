"""
occurrences_per_entity.py
A specialized Occurrences subclass that enforces one row per entity.
"""
from __future__ import annotations
import pandas as pd
from occurrences import Occurrences
from occurrence_semantics import OccurrenceSemantics

_ERROR_PREFIX = "[OccurrencesPerEntity] Error"


class OccurrencesPerEntity(Occurrences):
    """
    An Occurrences collection where each entity appears exactly once.

    Inherits all validation, triage, and functionality from Occurrences.
    Adds one additional constraint: entity_id_col must be unique across
    all rows in .data after triage.

    Useful for landmark events — index dates, first diagnoses,
    enrollment dates — where one date per entity is a structural requirement.

    Also provides build_span() to generate per-entity span windows
    centered on the occurrence date.
    """

    _ERROR_PREFIX = "[OccurrencesPerEntity] Error"

    def __init__(self, data_input: pd.DataFrame, semantics: OccurrenceSemantics) -> None:
        super().__init__(data_input, semantics)
        self._validate_one_row_per_entity()

    def _validate_one_row_per_entity(self) -> None:
        col = self.semantics.entity_id_col
        duplicated = self.data[self.data[col].duplicated(keep=False)]
        if not duplicated.empty:
            dupes = duplicated[col].unique().tolist()
            raise ValueError(
                f"{_ERROR_PREFIX}: entity_id_col '{col}' must be unique "
                f"across all rows. Duplicate entities found: {dupes}"
            )

    # ------------------------------------------------------------------ #
    # Build span
    # ------------------------------------------------------------------ #

    def build_span(self, window: tuple[int, int], span_semantics) -> "EventsPerEntity":
        """
        Build one span per entity centered on the occurrence date.

        Parameters
        ----------
        window : tuple[int, int]
            (before_days, after_days) — both non-negative integers.
            span_start = occurrence_date - before_days
            span_end   = occurrence_date + after_days
        span_semantics : EventSemantics
            Semantics for the output EventsPerEntity object.
            entity_id_col must match this object's entity_id_col.

        Returns
        -------
        EventsPerEntity
            One row per entity with span_start and span_end columns.

        Examples
        --------
        # Build a 1-year window around each diagnosis date
        spans = diagnoses.build_span(window=(365, 365), span_semantics=span_sem)
        """
        from events_per_entity import EventsPerEntity
        from occurrences_utils import build_span_from_occurrences

        if span_semantics.entity_id_col != self.semantics.entity_id_col:
            raise ValueError(
                f"{_ERROR_PREFIX} in build_span: span_semantics.entity_id_col "
                f"'{span_semantics.entity_id_col}' does not match "
                f"'{self.semantics.entity_id_col}'"
            )

        span_df = build_span_from_occurrences(
            data=self.data,
            semantics=self.semantics,
            span_semantics=span_semantics,
            window=window,
        )
        return EventsPerEntity(span_df, span_semantics)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        identity = f" ({self.semantics.identity})" if self.semantics.identity else ""
        return (
            f"OccurrencesPerEntity{identity}("
            f"{len(self)} entities, "
            f"entity_col='{self.semantics.entity_id_col}', "
            f"date_col='{self.semantics.date_col}')"
        )
