"""
occurrences_per_entity.py
OccurrencesPerEntity — a specialized Occurrences subclass that
enforces one row per entity.
"""
from __future__ import annotations
import pandas as pd

import sys
sys.path.append("C:/Users/DanielArenas/Desktop/Github_Local/Python_Events_Classes")
from data_objects.occurrences import Occurrences
from semantics.occurrence_semantics import OccurrenceSemantics

_ERROR_PREFIX = "[OccurrencesPerEntity] Error"


class OccurrencesPerEntity(Occurrences):
    """
    An Occurrences collection where each entity appears exactly once.

    Inherits all validation from Occurrences. Adds one additional
    constraint: entity_id_col must be unique across all rows.

    Useful for landmark events — index dates, first diagnoses,
    enrollment dates — where one occurrence per entity is a
    structural requirement.

    Also provides build_obs_period() to generate per-entity
    observation windows centered on the occurrence date.

    Raises
    ------
    ValueError
        If any entity appears more than once.
    """

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: OccurrenceSemantics,
    ) -> None:
        super().__init__(data, semantics)
        self._validate_one_row_per_entity()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate_one_row_per_entity(self) -> None:
        """Raise if any entity appears more than once."""
        col       = self.semantics.entity_id_col
        duplicated = self.data[self.data[col].duplicated(keep=False)]
        if not duplicated.empty:
            dupes = duplicated[col].unique().tolist()
            raise ValueError(
                f"{_ERROR_PREFIX}: entity_id_col '{col}' must be unique "
                f"across all rows. Duplicate entities found: "
                f"{dupes[:5]}{'...' if len(dupes) > 5 else ''}"
            )

    # ------------------------------------------------------------------ #
    # Public methods — override to return OccurrencesPerEntity
    # ------------------------------------------------------------------ #

    def filter_by_entities(self, entity_ids) -> "OccurrencesPerEntity":
        """Return a new OccurrencesPerEntity containing only the specified entities."""
        col      = self.semantics.entity_id_col
        filtered = self.data[self.data[col].isin(entity_ids)].copy()
        return OccurrencesPerEntity._from_clean(filtered, self.semantics)

    def copy(self) -> "OccurrencesPerEntity":
        """Return a copy of this OccurrencesPerEntity."""
        return OccurrencesPerEntity._from_clean(self.data.copy(), self.semantics)

    # ------------------------------------------------------------------ #
    # Build observation period
    # ------------------------------------------------------------------ #

    def build_obs_period(
        self,
        window:         tuple[int, int],
        span_semantics,
        identity:       str | None = None,
    ) -> "ObsPeriodPerEntity":
        """
        Build one observation period per entity centered on the occurrence date.

        Parameters
        ----------
        window : tuple[int, int]
            (before_days, after_days) — both non-negative integers.
            span_start = occurrence_date - before_days
            span_end   = occurrence_date + after_days
        span_semantics : EventSemantics
            Semantics for the output ObsPeriodPerEntity.
            entity_id_col must match this object's entity_id_col.
        identity : str | None
            Identity label for the observation period.
            Default 'general_entity'.

        Returns
        -------
        ObsPeriodPerEntity
            One row per entity with span_start and span_end columns.

        Examples
        --------
        >>> obs = diagnoses.build_obs_period(
        ...     window         = (365, 365),
        ...     span_semantics = span_sem,
        ...     identity       = "post_diagnosis_window",
        ... )
        """
        from .obs_period_per_entity import ObsPeriodPerEntity
        from .occurrences_utils import build_span_from_occurrences

        if span_semantics.entity_id_col != self.semantics.entity_id_col:
            raise ValueError(
                f"{_ERROR_PREFIX} in build_obs_period: "
                f"span_semantics.entity_id_col "
                f"'{span_semantics.entity_id_col}' does not match "
                f"'{self.semantics.entity_id_col}'"
            )

        span_df = build_span_from_occurrences(
            data           = self.data,
            semantics      = self.semantics,
            span_semantics = span_semantics,
            window         = window,
        )
        return ObsPeriodPerEntity(span_df, span_semantics, identity=identity)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"OccurrencesPerEntity(\n"
            f"  identity   : {self.semantics.identity!r}\n"
            f"  entities   : {len(self):,}\n"
            f"  entity_col : '{self.semantics.entity_id_col}'\n"
            f"  date_col   : '{self.semantics.date_col}'\n"
            f")"
        )
