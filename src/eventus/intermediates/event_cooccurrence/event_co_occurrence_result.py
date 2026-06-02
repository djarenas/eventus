"""
event_co_occurrence_result.py
EventCoOccurrenceResult — abstract base class for all co-occurrence
result objects.

Subclasses
----------
EventCoOccurrencePresenceResult
EventCoOccurrenceGapResult
"""
from __future__ import annotations
from abc import ABC
import pandas as pd

_ERROR = "[EventCoOccurrenceResult] Error"

_REQUIRED_BASE_COLS = {"obs_start", "obs_end"}


class EventCoOccurrenceResult(ABC):
    """
    Abstract base class for all co-occurrence result objects.

    Holds a per-entity DataFrame with one row per entity, and carries
    the two event identities and entity column name. Never instantiated
    directly — use EventCoOccurrencePresenceResult or
    EventCoOccurrenceGapResult.

    Structural invariants
    ---------------------
    - data is a non-empty DataFrame
    - entity_col is present, non-null, and unique in data
    - obs_start and obs_end columns are present
    - identity_a and identity_b are non-empty strings
    - identity_a != identity_b
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _data:       pd.DataFrame  # validated per-entity DataFrame, index reset
    _entity_col: str           # entity identifier column name
    _identity_a: str           # first event identity label
    _identity_b: str           # second event identity label

    def __init__(
        self,
        data:       pd.DataFrame,
        entity_col: str,
        identity_a: str,
        identity_b: str,
    ) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR}: data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if data.empty:
            raise ValueError(f"{_ERROR}: data must not be empty.")

        if not isinstance(entity_col, str) or not entity_col.strip():
            raise TypeError(
                f"{_ERROR}: entity_col must be a non-empty string, "
                f"got {entity_col!r}"
            )
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' not found in data. "
                f"Available columns: {sorted(data.columns.tolist())}"
            )
        if data[entity_col].isnull().any():
            n = int(data[entity_col].isnull().sum())
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' has {n} null value(s)."
            )
        if data[entity_col].duplicated().any():
            dupes = data[entity_col][data[entity_col].duplicated()].tolist()
            raise ValueError(
                f"{_ERROR}: entity_col '{entity_col}' is not unique. "
                f"Duplicate values: {dupes[:5]}"
                f"{'...' if len(dupes) > 5 else ''}. "
                f"EventCoOccurrenceResult requires one row per entity."
            )

        missing = _REQUIRED_BASE_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR}: data is missing required columns: {sorted(missing)}."
            )

        for name, val in [("identity_a", identity_a), ("identity_b", identity_b)]:
            if not isinstance(val, str) or not val.strip():
                raise TypeError(
                    f"{_ERROR}: {name} must be a non-empty string, "
                    f"got {val!r}"
                )
        if identity_a == identity_b:
            raise ValueError(
                f"{_ERROR}: identity_a and identity_b must be different, "
                f"got '{identity_a}' for both."
            )

        self._data       = data.reset_index(drop=True).copy()
        self._entity_col = entity_col
        self._identity_a = identity_a
        self._identity_b = identity_b

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
    def identity_a(self) -> str:
        return self._identity_a

    @property
    def identity_b(self) -> str:
        return self._identity_b

    @property
    def n_entities(self) -> int:
        return len(self._data)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._data)
