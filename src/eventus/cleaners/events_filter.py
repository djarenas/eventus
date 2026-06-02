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
    ...     .to_obs_period(obs)
    ...     .result
    ... )
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _events: Events  # the current filtered Events object

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
        col      = self._events.semantics.entity_id_col
        mask     = self._events.data[col].isin(entity_ids)
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

        Filters on the single event date column.

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

        dc  = self._events.semantics.date_col
        df  = self._events.data.copy()

        if start is not None:
            if start_bound == DateBoundary.INCLUSIVE:
                df = df[df[dc] >= start]
            else:
                df = df[df[dc] > start]

        if end is not None:
            if end_bound == DateBoundary.INCLUSIVE:
                df = df[df[dc] <= end]
            else:
                df = df[df[dc] < end]

        return EventsFilter(
            Events._construct_from_cleaned(df, self._events.semantics)
        )

    def to_obs_period(
        self,
        obs_period,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "EventsFilter":
        """
        Filter events to each entity's observation period.

        Only entities present in obs_period are kept. Events
        outside the entity's obs window are dropped. Unlike episodes,
        events are point-in-time so there is no clipping —
        they either fall inside the window or they don't.

        Parameters
        ----------
        obs_period : ObsPeriodPerEntity
            One row per entity defining the observation window.
            entity_id_col must match events.semantics.entity_id_col.
        start_bound : DateBoundary
            INCLUSIVE (>=) or EXCLUSIVE (>) for the obs_start boundary.
            Default INCLUSIVE.
        end_bound : DateBoundary
            INCLUSIVE (<=) or EXCLUSIVE (<) for the obs_end boundary.
            Default INCLUSIVE.

        Returns
        -------
        EventsFilter
            Wrapping a new Events filtered to each entity's
            observation period.

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
        date_col      = self._events.semantics.date_col

        # Merge obs window onto events
        obs_lookup = obs_period.data.set_index(obs_entity_col)[
            [obs_start_col, obs_end_col]
        ].rename(columns={
            obs_start_col: "_obs_start",
            obs_end_col:   "_obs_end",
        })

        df = self._events.data.merge(
            obs_lookup,
            left_on     = evt_entity_col,
            right_index = True,
            how         = "inner",  # drops entities not in obs_period
        )

        # Apply bounds — events are point-in-time, no clipping needed
        if start_bound == DateBoundary.INCLUSIVE:
            inside_start = df[date_col] >= df["_obs_start"]
        else:
            inside_start = df[date_col] > df["_obs_start"]

        if end_bound == DateBoundary.INCLUSIVE:
            inside_end = df[date_col] <= df["_obs_end"]
        else:
            inside_end = df[date_col] < df["_obs_end"]

        df = df[inside_start & inside_end].copy()
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
