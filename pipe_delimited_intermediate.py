"""
pipe_delimited_intermediate.py
Base class for pipe-delimited intermediate DataFrames.
Universal handshake format between analysis classes and visualization classes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd

_ERROR_PREFIX = "[PipeDelimitedIntermediate] Error"

# Fixed column names
ENTITY_ID_COL    = "entity_id"
SPAN_START_COL   = "span_start"
SPAN_END_COL     = "span_end"
EVENT_STARTS_COL = "event_starts"
EVENT_ENDS_COL   = "event_ends"

_SPAN_PAIR   = {SPAN_START_COL, SPAN_END_COL}
_EVENT_PAIR  = {EVENT_STARTS_COL, EVENT_ENDS_COL}


class PipeDelimitedIntermediate:
    """
    A validated DataFrame wrapper that serves as the universal handshake
    format between analysis classes and visualization classes.

    One row per entity. All multi-value columns are pipe-delimited strings.

    Required columns:
        entity_id

    Optional paired columns (must have both or neither):
        span_start + span_end
        event_starts + event_ends

    Optional occurrence columns (any number):
        Any column prefixed with 'occ_' is treated as an occurrence column.
        Named by occurrence identity with spaces replaced by underscores,
        e.g. 'occ_hepatitis_b_vaccination'.
        Values are pipe-delimited date strings.

    Attributes
    ----------
    data : pd.DataFrame
        The validated intermediate DataFrame.
    entity_col : str
        Name of the entity identifier column (always 'entity_id').
    """

    def __init__(self, data: pd.DataFrame, entity_col: str = ENTITY_ID_COL) -> None:
        self._validate(data, entity_col)
        self.data       = data.reset_index(drop=True)
        self.entity_col = entity_col

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(data: pd.DataFrame, entity_col: str) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a DataFrame, "
                f"got {type(data).__name__}"
            )
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR_PREFIX}: entity column '{entity_col}' not found in data"
            )
        if data[entity_col].isna().any():
            raise ValueError(
                f"{_ERROR_PREFIX}: entity column '{entity_col}' contains null values"
            )
        # Validate optional pairs
        cols = set(data.columns)
        for pair_name, pair in [("span", _SPAN_PAIR), ("event", _EVENT_PAIR)]:
            present = pair & cols
            if len(present) == 1:
                missing = pair - present
                raise ValueError(
                    f"{_ERROR_PREFIX}: '{list(present)[0]}' is present but "
                    f"'{list(missing)[0]}' is missing — "
                    f"{pair_name} columns must appear together"
                )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def has_spans(self) -> bool:
        return SPAN_START_COL in self.data.columns

    @property
    def has_events(self) -> bool:
        return EVENT_STARTS_COL in self.data.columns

    @property
    def occurrence_cols(self) -> list[str]:
        """Returns list of occurrence column names (prefixed with 'occ_')."""
        return [c for c in self.data.columns if c.startswith("occ_")]

    @property
    def occurrence_identities(self) -> list[str]:
        """Returns occurrence identities derived from column names."""
        return [c[4:].replace("_", " ") for c in self.occurrence_cols]

    # ------------------------------------------------------------------ #
    # Class methods
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        entity_col: str = ENTITY_ID_COL,
    ) -> "PipeDelimitedIntermediate":
        """
        Build a PipeDelimitedIntermediate from an existing DataFrame.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain at minimum the entity column.
        entity_col : str
            Name of the entity identifier column. Default 'entity_id'.
        """
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def identity_to_col(identity: str) -> str:
        """Convert an occurrence identity string to a column name."""
        return "occ_" + identity.lower().replace(" ", "_")

    @staticmethod
    def col_to_identity(col: str) -> str:
        """Convert an occurrence column name back to an identity string."""
        return col[4:].replace("_", " ")

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def self_validate(self) -> "pd.DataFrame":
        """
        Validate the content of all pipe-delimited date columns.

        Checks that all date strings are parseable, that paired columns
        have matching token counts, and that span_start <= span_end.

        Returns
        -------
        pd.DataFrame
            Rows that failed validation with a '_validation_reason' column.
            Empty DataFrame if all rows are valid.
        """
        from pipe_delimited_utils import validate_content
        return validate_content(self.data, self.entity_col)

    @classmethod
    def combine(cls, *intermediates) -> "PipeDelimitedIntermediate":
        """
        Combine two or more PipeDelimitedIntermediate objects into one.

        All intermediates must share the same entity_col and the same
        set of entities. Columns from each intermediate are merged — if
        a column exists in multiple intermediates the last one wins.

        Parameters
        ----------
        *intermediates : PipeDelimitedIntermediate
            Two or more intermediate objects to combine.

        Returns
        -------
        PipeDelimitedIntermediate
            A new base-class intermediate with all columns merged.

        Raises
        ------
        ValueError
            If entity_col values differ or entity sets differ.
        """
        if len(intermediates) < 2:
            raise ValueError(
                "[PipeDelimitedIntermediate] combine() requires at least 2 intermediates"
            )

        # Validate all inputs are PipeDelimitedIntermediate or subclasses
        for i, obj in enumerate(intermediates):
            if not isinstance(obj, PipeDelimitedIntermediate):
                raise TypeError(
                    f"[PipeDelimitedIntermediate] combine(): intermediates[{i}] "
                    f"must be a PipeDelimitedIntermediate or subclass, "
                    f"got {type(obj).__name__}"
                )

        entity_col = intermediates[0].entity_col
        for i, obj in enumerate(intermediates[1:], 1):
            if obj.entity_col != entity_col:
                raise ValueError(
                    f"[PipeDelimitedIntermediate] combine(): entity_col mismatch — "
                    f"intermediates[0] has '{entity_col}', "
                    f"intermediates[{i}] has '{obj.entity_col}'"
                )

        # Start with first intermediate's data, merge rest in
        combined = intermediates[0].data.copy()
        for obj in intermediates[1:]:
            new_cols = [c for c in obj.data.columns if c != entity_col]
            combined = combined.merge(
                obj.data[[entity_col] + new_cols],
                on=entity_col,
                how="outer",
                suffixes=("", "_dup"),
            )
            # Drop any duplicate columns
            dup_cols = [c for c in combined.columns if c.endswith("_dup")]
            combined = combined.drop(columns=dup_cols)

        return cls(combined, entity_col)

    def to_csv(self, path: str) -> None:
        """Save the intermediate DataFrame to CSV."""
        self.data.to_csv(path, index=False)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        parts = [f"PipeDelimitedIntermediate({len(self)} entities"]
        if self.has_spans:
            parts.append("spans=yes")
        if self.has_events:
            parts.append("events=yes")
        if self.occurrence_cols:
            parts.append(f"occurrences={self.occurrence_identities}")
        return ", ".join(parts) + ")"
