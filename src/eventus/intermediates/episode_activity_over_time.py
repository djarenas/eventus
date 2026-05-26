"""
episode_activity_over_time.py
EpisodeActivityOverTime — validated result object from
CohortTimelineEpisodeAnalyzer.compute_activity_over_time().

Carries the timeseries DataFrame, the x-axis mode, and (when
mode='calendar') the cohort_start date needed to reconstruct
calendar dates from day offsets.
"""
from __future__ import annotations
import pandas as pd

_ERROR = "[EpisodeActivityOverTime] Error"

_REQUIRED_COLS = {"day", "n_total", "n_active", "pct_active", "n_entered", "n_exited"}
_VALID_MODES   = {"normalized", "calendar"}


class EpisodeActivityOverTime:
    """
    I am the result of CohortTimelineEpisodeAnalyzer.compute_activity_over_time(), 
    I carry a validated timeseries DataFrame, the x-axis mode, and cohort_start when mode is 'calendar'.

    Attributes
    ----------
    data : pd.DataFrame
        Columns: day (int), n_total (int), n_active (int),
        pct_active (float), n_entered (int | NA), n_exited (int | NA).
        One row per timepoint bucket.
    mode : str
        'normalized' — day 0 is each entity's own obs_start.
        'calendar'   — day 0 is cohort_start (shared across all entities).
    cohort_start : pd.Timestamp | None
        The shared obs_start date when mode='calendar', normalized to
        midnight. None when mode='normalized'.

    Raises at construction if:
    - mode is not 'normalized' or 'calendar'
    - data is missing required columns or is empty
    - cohort_start is provided but not coercible to pd.Timestamp
    - mode='calendar' but cohort_start is None
    - mode='normalized' but cohort_start is not None
    """

    _data:         pd.DataFrame
    _mode:         str
    _cohort_start: pd.Timestamp | None

    def __init__(
        self,
        data:         pd.DataFrame,
        mode:         str,
        cohort_start: pd.Timestamp | str | None = None,
    ) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR} data must be a pandas DataFrame, "
                f"got {type(data).__name__}"
            )
        if mode not in _VALID_MODES:
            raise ValueError(
                f"{_ERROR} mode must be one of {sorted(_VALID_MODES)}, "
                f"got {mode!r}"
            )

        missing = _REQUIRED_COLS - set(data.columns)
        if missing:
            raise ValueError(
                f"{_ERROR} data is missing required columns: {sorted(missing)}. "
                f"Required: {sorted(_REQUIRED_COLS)}"
            )
        if data.empty:
            raise ValueError(
                f"{_ERROR} data must not be empty."
            )

        # Resolve and validate cohort_start
        resolved_start: pd.Timestamp | None = None
        if cohort_start is not None:
            try:
                resolved_start = pd.Timestamp(cohort_start).normalize()
            except Exception:
                raise ValueError(
                    f"{_ERROR} cohort_start must be a date, datetime string, "
                    f"or pd.Timestamp, got {cohort_start!r}"
                )

        if mode == "calendar" and resolved_start is None:
            raise ValueError(
                f"{_ERROR} cohort_start is required when mode='calendar'."
            )
        if mode == "normalized" and resolved_start is not None:
            raise ValueError(
                f"{_ERROR} cohort_start must be None when mode='normalized'."
            )

        self._data         = data.reset_index(drop=True).copy()
        self._mode         = mode
        self._cohort_start = resolved_start

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def cohort_start(self) -> pd.Timestamp | None:
        return self._cohort_start

    @property
    def max_days(self) -> int:
        return int(self._data["day"].max())

    @property
    def n_entities(self) -> int:
        return int(self._data["n_total"].iloc[0])

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return (
            f"EpisodeActivityOverTime(\n"
            f"  mode         : '{self._mode}'\n"
            f"  cohort_start : {self._cohort_start}\n"
            f"  timepoints   : {len(self._data):,}\n"
            f"  max_days     : {self.max_days:,}\n"
            f"  n_entities   : {self.n_entities:,}\n"
            f")"
        )
