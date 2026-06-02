"""
episodes.py
Episodes — a boring, but validated, container for episode data.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from eventus.semantics.episode_semantics import EpisodeSemantics

_ERROR_PREFIX = "[Episodes] Error"


class Episodes:
    """
    A validated container for episode data.

    Holds a DataFrame of episodes with start and end times.
    Validates structure at construction — if an Episodes object exists,
    it is structurally sound. Row-level cleaning is the responsibility
    of EpisodesCleaner.

    Parameters
    ----------
    data : pd.DataFrame
        Structurally valid episode data. No nulls in entity_id,
        start_time, or end_time columns.
    semantics : EpisodeSemantics
        Column mapping for entity_id, start_time, end_time.

    Examples
    --------
    >>> # From clean data
    >>> episodes = Episodes(df, sem)

    >>> # From messy data — clean first
    >>> episodes = EpisodesCleaner(df, sem, config).clean()
    """

    # ── Attributes ───────────────────────────────────────────────────────
    data:      pd.DataFrame      # validated episode rows, index reset
    semantics: EpisodeSemantics  # column mappings and identity label

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EpisodeSemantics,
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
        self, data: pd.DataFrame, semantics: EpisodeSemantics
    ) -> None:
        """Raise if data is not a DataFrame or semantics is not EpisodeSemantics."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if not isinstance(semantics, EpisodeSemantics):
            raise TypeError(
                f"{_ERROR_PREFIX}: semantics must be an EpisodeSemantics object, "
                f"got {type(semantics).__name__}"
            )

    def _validate_columns(
        self, data: pd.DataFrame, sem: EpisodeSemantics
    ) -> None:
        """Raise if any required columns are missing."""
        required = [sem.entity_id_col, sem.start_time_col, sem.end_time_col]
        if sem.episode_id_col:   required.append(sem.episode_id_col)
        if sem.episode_type_col: required.append(sem.episode_type_col)
        required.extend(sem.metadata_cols)
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: missing required columns: {missing}"
            )

    def _parse_dates(
        self, data: pd.DataFrame, sem: EpisodeSemantics
    ) -> pd.DataFrame:
        """Parse start and end columns to datetime. Returns modified DataFrame."""
        data = data.copy()
        for col in [sem.start_time_col, sem.end_time_col]:
            data[col] = pd.to_datetime(data[col], errors="coerce")
        return data

    def _validate_no_nulls(
        self, data: pd.DataFrame, sem: EpisodeSemantics
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
                f"Use EpisodesCleaner to handle these before constructing Episodes."
            )

    def _validate_causality(
        self, data: pd.DataFrame, sem: EpisodeSemantics
    ) -> None:
        """Raise if any episode has start strictly after end."""
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
                f"Use EpisodesCleaner to swap or remove these rows before "
                f"constructing Episodes."
            )

    # ------------------------------------------------------------------ #
    # Class methods
    # ------------------------------------------------------------------ #

    @classmethod
    def _construct_from_cleaned(cls, data: pd.DataFrame, semantics: EpisodeSemantics) -> "Episodes":
        """
        Bypass validation to construct an Episodes from already-clean data.
        Only used internally — never call this on unvalidated data.
        """
        obj           = object.__new__(cls)
        obj.data      = data.copy().reset_index(drop=True)
        obj.semantics = semantics
        return obj

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def copy(self) -> "Episodes":
        """Return a copy of this Episodes object."""
        return Episodes._construct_from_cleaned(self.data.copy(), self.semantics)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (
            f"Episodes(\n"
            f"  rows             : {len(self):,}\n"
            f"  unique entities  : {self.data[self.semantics.entity_id_col].nunique():,}\n"
            f"  entity_col       : '{self.semantics.entity_id_col}'\n"
            f"  start_col        : '{self.semantics.start_time_col}'\n"
            f"  end_col          : '{self.semantics.end_time_col}'\n"
            f")"
        )