"""
episode_duration_result.py
EpisodeDurationResult — validated result object from EpisodeDurationAnalyzer.

One row per episode. Carries duration_days and optional descriptor columns.
Stratification is a view on the data, not a property of the result —
call build_arrays(stratify_by=...) at plot time.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

_ERROR = "[EpisodeDurationResult] Error"

_REQUIRED_COLS = {"duration_days"}


class EpisodeDurationResult:
    """
    I am the result of EpisodeDurationAnalyzer.calc(). I hold per-episode
    duration data and optional descriptor columns. I know my identity
    and my entity column. I do not know how I will be visualized.

    Structural invariants
    ---------------------
    - data is a non-empty DataFrame
    - entity_col is present and non-null in data
    - duration_days is present and non-null in data
    - duration_days is non-negative (guaranteed by Episodes causality check)
    - descriptor columns may have nulls — that is by design
    - entity_col is NOT required to be unique — one entity may have
      multiple episodes

    Parameters
    ----------
    data : pd.DataFrame
        One row per episode. Must contain entity_col and duration_days.
        May contain additional descriptor columns.
    entity_col : str
        Name of the entity identifier column.
    identity : str | None
        Episode identity label from EpisodeSemantics. May be None.
    descriptor_cols : list[str]
        Names of descriptor columns present in data.
        Nulls in these columns are allowed.
    """

    _data:            pd.DataFrame
    _entity_col:      str
    _identity:        str | None
    _descriptor_cols: list[str]

    def __init__(
        self,
        data:            pd.DataFrame,
        entity_col:      str,
        identity:        str | None  = None,
        descriptor_cols: list[str]   = None,
    ) -> None:
        if descriptor_cols is None:
            descriptor_cols = []

        # ── Type checks ───────────────────────────────────────────────
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
        if identity is not None and (
            not isinstance(identity, str) or not identity.strip()
        ):
            raise TypeError(
                f"{_ERROR} identity must be a non-empty string or None, "
                f"got {identity!r}"
            )
        if not isinstance(descriptor_cols, list):
            raise TypeError(
                f"{_ERROR} descriptor_cols must be a list, "
                f"got {type(descriptor_cols).__name__}"
            )

        # ── Required columns ──────────────────────────────────────────
        missing = (_REQUIRED_COLS | {entity_col}) - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}."
            )

        # ── entity_col must be non-null ───────────────────────────────
        if data[entity_col].isnull().any():
            n = int(data[entity_col].isnull().sum())
            raise ValueError(
                f"{_ERROR} entity_col '{entity_col}' has {n} null value(s). "
                f"Every episode must have an entity identifier."
            )

        # ── duration_days must be non-null and non-negative ───────────
        if data["duration_days"].isnull().any():
            n = int(data["duration_days"].isnull().sum())
            raise ValueError(
                f"{_ERROR} duration_days has {n} null value(s). "
                f"Every episode must have a computed duration."
            )
        if (data["duration_days"] < 0).any():
            n = int((data["duration_days"] < 0).sum())
            raise ValueError(
                f"{_ERROR} duration_days has {n} negative value(s). "
                f"Negative durations are not valid — check Episodes causality."
            )

        # ── descriptor_cols must exist in data ────────────────────────
        missing_desc = [c for c in descriptor_cols if c not in data.columns]
        if missing_desc:
            raise ValueError(
                f"{_ERROR} descriptor_cols not found in data: {missing_desc}. "
                f"Available columns: {sorted(data.columns.tolist())}"
            )

        self._data            = data.reset_index(drop=True).copy()
        self._entity_col      = entity_col
        self._identity        = identity
        self._descriptor_cols = list(descriptor_cols)

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
    def identity(self) -> str | None:
        return self._identity

    @property
    def descriptor_cols(self) -> list[str]:
        return list(self._descriptor_cols)

    @property
    def n_episodes(self) -> int:
        """Total number of episodes (rows)."""
        return len(self._data)

    @property
    def n_entities(self) -> int:
        """Number of unique entities."""
        return self._data[self._entity_col].nunique()

    # ------------------------------------------------------------------ #
    # build_arrays
    # ------------------------------------------------------------------ #

    def build_arrays(
        self,
        stratify_by: str | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Build a {key: np.ndarray} dict of duration_days arrays,
        ready for ArraysViolinPlotter.

        "all_data" is always included as the first key, containing
        all duration values.

        If stratify_by is provided, one additional key per unique
        category value is added. stratify_by must be a column present
        in data — typically a descriptor column or the entity_col.

        Parameters
        ----------
        stratify_by : str | None
            Column name to stratify by. Must exist in data.
            Null values in this column are grouped under "missing".
            Default None — returns {"all_data": array} only.

        Returns
        -------
        dict[str, np.ndarray]
            "all_data" always first, then per-category keys if stratified.
            Values are 1-D float arrays of duration_days.

        Raises
        ------
        ValueError
            If stratify_by is not None and the column is not in data.
        """
        durations = self._data["duration_days"].to_numpy(dtype=np.float64)
        arrays: dict[str, np.ndarray] = {"all_data": durations}

        if stratify_by is None:
            return arrays

        if stratify_by not in self._data.columns:
            raise ValueError(
                f"{_ERROR} in build_arrays(): stratify_by column "
                f"'{stratify_by}' not found in data. "
                f"Available columns: {sorted(self._data.columns.tolist())}"
            )

        strat_col = self._data[stratify_by].fillna("missing").astype(str)
        for category in sorted(strat_col.unique()):
            mask = strat_col == category
            arrays[category] = (
                self._data.loc[mask, "duration_days"]
                .to_numpy(dtype=np.float64)
            )

        return arrays

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return self.n_episodes

    def __repr__(self) -> str:
        desc = (
            f"{self._descriptor_cols}"
            if self._descriptor_cols
            else "none"
        )
        return (
            f"EpisodeDurationResult:\n"
            f"  identity        : {self._identity!r}\n"
            f"  entity_col      : '{self._entity_col}'\n"
            f"  n_episodes        : {self.n_episodes:,}\n"
            f"  n_entities      : {self.n_entities:,}\n"
            f"  mean_duration   : {self._data['duration_days'].mean():.1f} days\n"
            f"  median_duration : {self._data['duration_days'].median():.1f} days\n"
            f"  descriptor_cols : {desc}\n"
        )
