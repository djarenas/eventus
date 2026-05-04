"""
obs_period_per_entity.py
ObsPeriodPerEntity — one observation window per entity.

The third level of the event hierarchy:
    Events
        ↓ (one row per entity)
    EventsPerEntity
        ↓ (semantic meaning: observation window)
    ObsPeriodPerEntity

Default output column names for classmethods:
    entity_id_col  → caller-supplied entity_col parameter
    start_time_col → "obs_start"
    end_time_col   → "obs_end"

Power users who need custom column names use direct construction:
    ObsPeriodPerEntity(df, full_semantics, identity="...")
"""
from __future__ import annotations
import pandas as pd

# Add the inner package folder directly to sys.path  
import sys
sys.path.append(r"C:/Users/DanielArenas/Desktop/Github_Local/Python_Events_Classes")  

from data_objects.events_per_entity import EventsPerEntity
from semantics.event_semantics import EventSemantics

_ERROR_PREFIX = "[ObsPeriodPerEntity] Error"

# Default output column names for all classmethods
_OBS_START_COL = "obs_start"
_OBS_END_COL   = "obs_end"
_DEFAULT_IDENTITY = "general_entity"


class ObsPeriodPerEntity(EventsPerEntity):
    """
    One observation window per entity.

    Each row defines the period within which that entity's events
    and occurrences are analyzed. Four construction paths:

    - Direct construction from a DataFrame (full control)
    - construct_from_calendar()   — same dates for all entities
    - construct_from_age_window() — per-entity dates derived from date of birth
    - construct_from_events()     — first event start to last event end

    Classmethods produce output with standard column names:
        obs_start, obs_end
    Direct construction accepts any column names via EventSemantics.

    Parameters
    ----------
    data : pd.DataFrame
        One row per entity with start and end date columns.
    semantics : EventSemantics
        Column mapping. identity attribute names the obs period.
        Only letters, numbers, and underscores allowed.
    identity : str | None
        Name for this observation period. Overrides semantics.identity
        if provided. Default 'general_entity'.

    Examples
    --------
    >>> # Direct — full control over column names
    >>> obs = ObsPeriodPerEntity(spans_df, sem, identity="medicaid_2022")

    >>> # Calendar period — output has obs_start, obs_end
    >>> obs = ObsPeriodPerEntity.construct_from_calendar(
    ...     entity_ids = events.data["patient_id"].unique(),
    ...     start      = "2022-01-01",
    ...     end        = "2022-12-31",
    ...     entity_col = "patient_id",
    ...     identity   = "medicaid_2022",
    ... )

    >>> # Age window — output has obs_start, obs_end
    >>> obs = ObsPeriodPerEntity.construct_from_age_window(
    ...     entity_df  = patients_df,
    ...     dob_col    = "date_of_birth",
    ...     age_start  = 65,
    ...     age_end    = 70,
    ...     entity_col = "patient_id",
    ...     identity   = "age_65_to_70",
    ... )

    >>> # From events — reuses events.semantics column names
    >>> obs = ObsPeriodPerEntity.construct_from_events(events, identity="hospitalization_window")
    """

    _DEFAULT_IDENTITY = _DEFAULT_IDENTITY

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EventSemantics,
        identity:  str | None = None,
    ) -> None:
        from .obs_period_per_entity_utils import validate_identity

        self._identity          = identity or self._DEFAULT_IDENTITY
        self._construction_path = "direct"

        validate_identity(self._identity)
        super().__init__(data, semantics)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def construction_path(self) -> str:
        return self._construction_path

    # ------------------------------------------------------------------ #
    # Internal helper — build default semantics for classmethods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _default_semantics(entity_col: str) -> EventSemantics:
        """Build standard semantics with obs_start / obs_end column names."""
        return EventSemantics(
            entity_id_col  = entity_col,
            start_time_col = _OBS_START_COL,
            end_time_col   = _OBS_END_COL,
        )

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def construct_from_calendar(
        cls,
        entity_ids: list,
        start:      str,
        end:        str,
        entity_col: str,
        identity:   str | None = None,
    ) -> "ObsPeriodPerEntity":
        """
        Build an ObsPeriodPerEntity with the same observation period
        for every entity. Output columns: obs_start, obs_end.

        Parameters
        ----------
        entity_ids : list
            Unique entity identifiers. Raises if duplicates found.
        start : str
            Observation period start date (ISO format e.g. '2022-01-01').
        end : str
            Observation period end date (ISO format e.g. '2022-12-31').
        entity_col : str
            Name of the entity identifier column.
        identity : str | None
            Name for this observation period. Default 'general_entity'.

        Returns
        -------
        ObsPeriodPerEntity
            Output columns: {entity_col}, obs_start, obs_end.
        """
        from .obs_period_per_entity_utils import (
            build_calendar_spans, warn_future_dates
        )

        semantics = cls._default_semantics(entity_col)

        df = build_calendar_spans(
            entity_ids = entity_ids,
            start      = start,
            end        = end,
            entity_col = entity_col,
            start_col  = _OBS_START_COL,
            end_col    = _OBS_END_COL,
        )

        warn_future_dates(df, _OBS_START_COL, _OBS_END_COL, entity_col)

        obj = cls(df, semantics, identity=identity)
        obj._construction_path = "construct_from_calendar"
        return obj

    @classmethod
    def construct_from_age_window(
        cls,
        entity_df:  pd.DataFrame,
        dob_col:    str,
        age_start:  int,
        age_end:    int,
        entity_col: str,
        age_unit:   str        = "years",
        identity:   str | None = None,
    ) -> "ObsPeriodPerEntity":
        """
        Build an ObsPeriodPerEntity where each entity's window is
        derived from their date of birth and an age range.
        Output columns: obs_start, obs_end.

        Parameters
        ----------
        entity_df : pd.DataFrame
            Must contain entity_col and dob_col.
            Raises if any entity has a null date of birth.
        dob_col : str
            Column containing date of birth.
        age_start : int
            Start of observation window.
        age_end : int
            End of observation window. Must be greater than age_start.
        entity_col : str
            Name of the entity identifier column.
        age_unit : str
            Unit for age_start and age_end. "years" (default) or "months".
            Use "months" for pediatric cohorts e.g. age_start=6, age_end=18.
        identity : str | None
            Name for this observation period. Default 'general_entity'.

        Returns
        -------
        ObsPeriodPerEntity
            Output columns: {entity_col}, obs_start, obs_end.

        Examples
        --------
        >>> # Ages 65-70 years
        >>> obs = ObsPeriodPerEntity.construct_from_age_window(
        ...     entity_df=demog_df, dob_col="dob",
        ...     age_start=65, age_end=70,
        ...     entity_col="patient_id",
        ... )

        >>> # Ages 6-18 months (pediatric)
        >>> obs = ObsPeriodPerEntity.construct_from_age_window(
        ...     entity_df=demog_df, dob_col="dob",
        ...     age_start=6, age_end=18,
        ...     entity_col="patient_id",
        ...     age_unit="months",
        ...     identity="age_6_to_18_months",
        ... )

        Notes
        -----
        Feb 29 birthdays are shifted to Feb 28 in non-leap years,
        with a warning.
        """
        from .obs_period_per_entity_utils import (
            validate_age_window, build_age_window_spans, warn_future_dates
        )

        validate_age_window(age_start, age_end, age_unit)

        semantics = cls._default_semantics(entity_col)

        df = build_age_window_spans(
            entity_df  = entity_df,
            dob_col    = dob_col,
            age_start  = age_start,
            age_end    = age_end,
            entity_col = entity_col,
            start_col  = _OBS_START_COL,
            end_col    = _OBS_END_COL,
            age_unit   = age_unit,
        )

        warn_future_dates(df, _OBS_START_COL, _OBS_END_COL, entity_col)

        obj = cls(df, semantics, identity=identity)
        obj._construction_path = (
            f"construct_from_age_window(age {age_start}→{age_end} {age_unit})"
        )
        return obj

    @classmethod
    def construct_from_events(
        cls,
        events,
        identity: str | None = None,
    ) -> "ObsPeriodPerEntity":
        """
        Build an ObsPeriodPerEntity from an Events object.
        Each entity's span runs from their first event start
        to their last event end. Reuses the Events column names.

        This is the broadest possible observation window — it captures
        the full range of activity for each entity. If a narrower
        window is needed, build the DataFrame manually.

        Parameters
        ----------
        events : Events
            A validated Events object. Column names are reused
            in the output ObsPeriodPerEntity.
        identity : str | None
            Name for this observation period. Default 'general_entity'.

        Returns
        -------
        ObsPeriodPerEntity
            Output uses same column names as events.semantics.
        """
        from .events import Events
        from .obs_period_per_entity_utils import (
            build_spans_construct_from_events, warn_future_dates
        )

        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR_PREFIX}: construct_from_events requires an Events object, "
                f"got {type(events).__name__}"
            )

        df = build_spans_construct_from_events(
            events_df      = events.data,
            entity_col     = events.semantics.entity_id_col,
            start_col      = events.semantics.start_time_col,
            end_col        = events.semantics.end_time_col,
            out_start_col  = events.semantics.start_time_col,
            out_end_col    = events.semantics.end_time_col,
        )

        warn_future_dates(
            df,
            events.semantics.start_time_col,
            events.semantics.end_time_col,
            events.semantics.entity_id_col,
        )

        obj = cls(df, events.semantics, identity=identity)
        obj._construction_path = "construct_from_events"
        return obj

    # ------------------------------------------------------------------ #
    # Methods
    # ------------------------------------------------------------------ #

    def filter_by_entities(self, entity_ids) -> "ObsPeriodPerEntity":
        """Return a new ObsPeriodPerEntity containing only the specified entities."""
        col      = self.semantics.entity_id_col
        filtered = self.data[self.data[col].isin(entity_ids)].copy()
        obj = ObsPeriodPerEntity(filtered, self.semantics, identity=self._identity)
        obj._construction_path = self._construction_path + " (filtered)"
        return obj

    def copy(self) -> "ObsPeriodPerEntity":
        """Return a copy of this ObsPeriodPerEntity."""
        obj = ObsPeriodPerEntity(
            self.data.copy(), self.semantics, identity=self._identity
        )
        obj._construction_path = self._construction_path
        return obj

    def summary(self) -> None:
        """Print a human-readable summary."""
        sc  = self.semantics.start_time_col
        ec  = self.semantics.end_time_col

        lengths = (self.data[ec] - self.data[sc]).dt.days

        print(f"ObsPeriodPerEntity summary")
        print(f"  identity           : {self._identity}")
        print(f"  construction path  : {self._construction_path}")
        print(f"{'─' * 48}")
        print(f"{'Total entities':<30}: {len(self.data):>10,}")
        print(f"{'Period length mean':<30}: {lengths.mean():>10.1f} days")
        print(f"{'Period length min':<30}: {int(lengths.min()):>10} days")
        print(f"{'Period length max':<30}: {int(lengths.max()):>10} days")
        print(f"{'Earliest start':<30}: {str(self.data[sc].min().date()):>10}")
        print(f"{'Latest end':<30}: {str(self.data[ec].max().date()):>10}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"ObsPeriodPerEntity(\n"
            f"  identity          : '{self._identity}'\n"
            f"  entities          : {len(self.data):,}\n"
            f"  construction_path : '{self._construction_path}'\n"
            f"  entity_col        : '{self.semantics.entity_id_col}'\n"
            f"  start_col         : '{self.semantics.start_time_col}'\n"
            f"  end_col           : '{self.semantics.end_time_col}'\n"
            f")"
        )
