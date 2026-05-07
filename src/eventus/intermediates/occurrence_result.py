"""
occurrence_result.py
OccurrenceResult — base class for all single-identity occurrence result objects.

Subclasses
----------
OccurrenceResultVolume
OccurrenceResultTiming
OccurrenceResultShape
"""
from __future__ import annotations
from abc import ABC
import pandas as pd

from .occurrence_result_utils import to_yaml_repr

_ERROR = "[OccurrenceResult] Error"

_REQUIRED_BASE_COLS = {"obs_start", "obs_end"}


class OccurrenceResult(ABC):
    """
    I am the base class for all single-identity occurrence result objects.
    I hold a per-entity DataFrame, validate it at construction, and provide
    shared properties and display logic.

    I am never instantiated directly — use OccurrenceVolume, OccurrenceTiming,
    or OccurrenceShape.

    Structural invariants
    ---------------------
    - data is a non-empty DataFrame
    - entity_col is present, non-null, and unique in data
    - obs_start and obs_end columns are present in data
    - identity is a non-empty string (overridden by OccurrencePairResult)
    """

    _data:       pd.DataFrame
    _entity_col: str
    _identity:   str

    def __init__(
        self,
        data:       pd.DataFrame,
        entity_col: str,
        identity:   str,
    ) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR} data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if data.empty:
            raise ValueError(
                f"{_ERROR} data must not be empty."
            )
        if not isinstance(entity_col, str) or not entity_col.strip():
            raise TypeError(
                f"{_ERROR} entity_col must be a non-empty string, "
                f"got {entity_col!r}"
            )
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR} entity_col '{entity_col}' not found in data. "
                f"Available columns: {sorted(data.columns.tolist())}"
            )
        if data[entity_col].isnull().any():
            n = int(data[entity_col].isnull().sum())
            raise ValueError(
                f"{_ERROR} entity_col '{entity_col}' has {n} null value(s). "
                f"Every entity must be identified."
            )
        if data[entity_col].duplicated().any():
            dupes = data[entity_col][data[entity_col].duplicated()].tolist()
            raise ValueError(
                f"{_ERROR} entity_col '{entity_col}' is not unique. "
                f"Duplicate values: {dupes[:10]}"
                f"{'...' if len(dupes) > 10 else ''}. "
                f"OccurrenceResult requires one row per entity."
            )

        missing = _REQUIRED_BASE_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}."
            )

        self._validate_identity(identity)

        self._data       = data.reset_index(drop=True).copy()
        self._entity_col = entity_col
        self._identity   = identity

    def _validate_identity(self, identity) -> None:
        """
        Validate the identity value. Overridden by OccurrencePairResult
        to accept tuple[str, str] instead of str.
        """
        if not isinstance(identity, str) or not identity.strip():
            raise TypeError(
                f"{_ERROR} identity must be a non-empty string, "
                f"got {identity!r}"
            )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    @property
    def entity_col(self) -> str:
        return self._entity_col

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def n_entities(self) -> int:
        return len(self._data)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return to_yaml_repr(
            self.__class__.__name__,
            self._repr_fields(),
        )

    def _repr_fields(self) -> dict:
        """
        Override in subclasses to provide class-specific repr fields.
        Base implementation shows shared fields only.
        """
        return {
            "identity"  : self._identity,
            "entity_col": self._entity_col,
            "entities"  : f"{self.n_entities:,}",
        }
