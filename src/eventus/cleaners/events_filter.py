"""
events_filter.py
EventsFilter — filter a validated Events object by entities,
date ranges, or observation periods.

Filters are chainable — each method returns a new EventsFilter
wrapping the filtered Events, so calls can be composed in sequence.

The original Events object is never mutated.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.events import Events
from eventus.types import DateBoundary

_ERROR = "[EventsFilter] Error"

_DEFAULT_BOUND = DateBoundary.INCLUSIVE


class EventsFilter:
    """
    I filter a validated Events object. I am chainable.

    Each filter method returns a new EventsFilter so calls can
    be composed. Call .result to retrieve the filtered Events.

    Parameters
    ----------
    events : Events
        A validated Events object to filter.

    Examples
    --------
    >>> from eventus.cleaners import EventsFilter
    >>> from eventus.types import DateBoundary
    >>>
    >>> filtered = (
    ...     EventsFilter(events)
    ...     .by_entities(my_entity_ids)
    ...     .by_dates(start="2022-01-01", end="2022-12-31")
    ...     .result
    ... )
    >>>
    >>> # Filter to an observation period
    >>> filtered = (
    ...     EventsFilter(events)
    ...     .to_obs_period(obs, clip=True)
    ...     .result
    ... )
    """

    def __init__(self, events: Events) -> None:
        if not isinstance(events, Events):
            raise TypeError(
                f"{_ERROR}: events must be an Events object, "
                f"got {type(events).__name__}"
            )
        self._events = events

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def result(self) -> Events:
        """Return the filtered Events object."""
        return self._events

    # ------------------------------------------------------------------ #
    # Filter methods
    # ------------------------------------------------------------------ #

    def by_entities(self, entity_ids) -> "EventsFilter":
        """
        Keep only events belonging to the specified entities.

        Parameters
        ----------
        entity_ids : list | set | pd.Series | np.ndarray
            Entity identifiers to keep.

        Returns
        -------
        EventsFilter
            Wrapping a new Events with only the matching rows.
        """
        col     = self._events.semantics.entity_id_col
        mask    = self._events.data[col].isin(entity_ids)
        filtered = self._events.data[mask].copy()
        return EventsFilter(
            Events._construct_from_cleaned(filtered, self._events.semantics)
        )

    def by_dates(
        self,
        start:       str | pd.Timestamp | None = None,
        end:         str | pd.Timestamp | None = None,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "EventsFilter":
        """
        Keep only events within the given date range.

        Filters on event start date against the start bound and
        event end date against the end bound.

        Parameters
        ----------
        start : str | pd.Timestamp | None
            Lower bound date. None means no lower bound.
        end : str | pd.Timestamp | None
            Upper bound date. None means no upper bound.
        start_bound : DateBoundary
            INCLUSIVE (>=) or EXCLUSIVE (>). Default INCLUSIVE.
        end_bound : DateBoundary
            INCLUSIVE (<=) or EXCLUSIVE (<). Default INCLUSIVE.

        Returns
        -------
        EventsFilter
            Wrapping a new Events with only the matching rows.

        Raises
        ------
        ValueError
            If neither start nor end is provided.
            If start > end after parsing.
        """
        if start is None and end is None:
            raise ValueError(
                f"{_ERROR} in by_dates(): "
                f"at least one of start or end must be provided."
            )

        if start is not None:
            try:
                start = pd.Timestamp(start)
            except Exception:
                raise ValueError(
                    f"{_ERROR} in by_dates(): "
                    f"start={start!r} could not be parsed as a date."
                )

        if end is not None:
            try:
                end = pd.Timestamp(end)
            except Exception:
                raise ValueError(
                    f"{_ERROR} in by_dates(): "
                    f"end={end!r} could not be parsed as a date."
                )

        if start is not None and end is not None and start > end:
            raise ValueError(
                f"{_ERROR} in by_dates(): "
                f"start ({start.date()}) must be before end ({end.date()})."
            )

        sc  = self._events.semantics.start_time_col
        ec  = self._events.semantics.end_time_col
        df  = self._events.data.copy()

        if start is not None:
            if start_bound == DateBoundary.INCLUSIVE:
                df = df[df[sc] >= start]
            else:
                df = df[df[sc] > start]

        if end is not None:
            if end_bound == DateBoundary.INCLUSIVE:
                df = df[df[ec] <= end]
            else:
                df = df[df[ec] < end]

        return EventsFilter(
            Events._construct_from_cleaned(df, self._events.semantics)
        )

    def to_obs_period(
        self,
        obs_period,
        clip:        bool  = True,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "EventsFilter":
        """
        Filter events to each entity's observation period.

        Only entities present in obs_period are kept. Events outside
        the entity's obs window are dropped. Events that partially
        overlap the window are either clipped to the boundary or
        dropped entirely, controlled by the clip parameter.

        Parameters
        ----------
        obs_period : ObsPeriodPerEntity
            One row per entity defining the observation window.
            entity_id_col must match events.semantics.entity_id_col.
        clip : bool
            If True (default), events that partially overlap the obs
            window are clipped to the boundary.
            If False, events that partially overlap are dropped.
        start_bound : DateBoundary
            INCLUSIVE (>=) or EXCLUSIVE (>) for the obs_start boundary.
            Default INCLUSIVE.
        end_bound : DateBoundary
            INCLUSIVE (<=) or EXCLUSIVE (<) for the obs_end boundary.
            Default INCLUSIVE.

        Returns
        -------
        EventsFilter
            Wrapping a new Events filtered and optionally clipped
            to each entity's observation period.

        Raises
        ------
        ValueError
            If entity_id_col does not match between events and obs_period.
        """
        from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERROR} in to_obs_period(): obs_period must be an "
                f"ObsPeriodPerEntity object, got {type(obs_period).__name__}"
            )

        evt_entity_col = self._events.semantics.entity_id_col
        obs_entity_col = obs_period.semantics.entity_id_col

        if evt_entity_col != obs_entity_col:
            raise ValueError(
                f"{_ERROR} in to_obs_period(): entity_id_col mismatch. "
                f"Events has '{evt_entity_col}', "
                f"obs_period has '{obs_entity_col}'."
            )

        obs_start_col = obs_period.semantics.start_time_col
        obs_end_col   = obs_period.semantics.end_time_col
        evt_start_col = self._events.semantics.start_time_col
        evt_end_col   = self._events.semantics.end_time_col

        # Merge obs window onto events
        obs_lookup = obs_period.data.set_index(obs_entity_col)[
            [obs_start_col, obs_end_col]
        ].rename(columns={
            obs_start_col: "_obs_start",
            obs_end_col:   "_obs_end",
        })

        df = self._events.data.merge(
            obs_lookup,
            left_on  = evt_entity_col,
            right_index = True,
            how      = "inner",  # drops entities not in obs_period
        )

        # Apply start bound
        if start_bound == DateBoundary.INCLUSIVE:
            overlaps_start = df[evt_end_col] >= df["_obs_start"]
        else:
            overlaps_start = df[evt_end_col] > df["_obs_start"]

        # Apply end bound
        if end_bound == DateBoundary.INCLUSIVE:
            overlaps_end = df[evt_start_col] <= df["_obs_end"]
        else:
            overlaps_end = df[evt_start_col] < df["_obs_end"]

        if clip:
            # Keep overlapping events and clip to obs boundaries
            df = df[overlaps_start & overlaps_end].copy()
            if start_bound == DateBoundary.INCLUSIVE:
                df[evt_start_col] = df[[evt_start_col, "_obs_start"]].max(axis=1)
            else:
                df[evt_start_col] = df[[evt_start_col, "_obs_start"]].max(axis=1)
            if end_bound == DateBoundary.INCLUSIVE:
                df[evt_end_col] = df[[evt_end_col, "_obs_end"]].min(axis=1)
            else:
                df[evt_end_col] = df[[evt_end_col, "_obs_end"]].min(axis=1)
        else:
            # Drop events that partially overlap — keep only fully contained
            if start_bound == DateBoundary.INCLUSIVE:
                fully_inside_start = df[evt_start_col] >= df["_obs_start"]
            else:
                fully_inside_start = df[evt_start_col] > df["_obs_start"]

            if end_bound == DateBoundary.INCLUSIVE:
                fully_inside_end = df[evt_end_col] <= df["_obs_end"]
            else:
                fully_inside_end = df[evt_end_col] < df["_obs_end"]

            df = df[fully_inside_start & fully_inside_end].copy()

        df = df.drop(columns=["_obs_start", "_obs_end"]).reset_index(drop=True)

        return EventsFilter(
            Events._construct_from_cleaned(df, self._events.semantics)
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._events)

    def __repr__(self) -> str:
        return (
            f"EventsFilter(\n"
            f"  events : {self._events!r}\n"
            f")"
        )
