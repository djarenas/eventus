"""
obs_period_filter.py
ObsPeriodFilter — filter a validated ObsPeriodPerEntity object
by entities or date range.

Filters are chainable — each method returns a new ObsPeriodFilter
wrapping the filtered ObsPeriodPerEntity, so calls can be composed
in sequence.

The original ObsPeriodPerEntity object is never mutated.

Note
----
ObsPeriodPerEntity defines one observation window per entity — it IS
the time window. Filtering by date here means keeping only entities
whose observation window falls within the given range, not clipping
the windows themselves. Use EventsFilter.to_obs_period() to clip
events to obs windows.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity
from eventus.types import DateBoundary

_ERROR = "[ObsPeriodFilter] Error"

_DEFAULT_BOUND = DateBoundary.INCLUSIVE


class ObsPeriodFilter:
    """
    I filter a validated ObsPeriodPerEntity object. I am chainable.

    Each filter method returns a new ObsPeriodFilter so calls can
    be composed. Call .result to retrieve the filtered ObsPeriodPerEntity.

    Parameters
    ----------
    obs_period : ObsPeriodPerEntity
        A validated ObsPeriodPerEntity object to filter.

    Examples
    --------
    >>> from eventus.cleaners import ObsPeriodFilter
    >>> from eventus.types import DateBoundary
    >>>
    >>> filtered = (
    ...     ObsPeriodFilter(obs)
    ...     .by_entities(my_entity_ids)
    ...     .by_dates(start="2022-01-01", end="2022-12-31")
    ...     .result
    ... )
    """

    def __init__(self, obs_period: ObsPeriodPerEntity) -> None:
        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERROR}: obs_period must be an ObsPeriodPerEntity object, "
                f"got {type(obs_period).__name__}"
            )
        self._obs = obs_period

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def result(self) -> ObsPeriodPerEntity:
        """Return the filtered ObsPeriodPerEntity object."""
        return self._obs

    # ------------------------------------------------------------------ #
    # Filter methods
    # ------------------------------------------------------------------ #

    def by_entities(self, entity_ids) -> "ObsPeriodFilter":
        """
        Keep only entities in the specified list.

        Parameters
        ----------
        entity_ids : list | set | pd.Series | np.ndarray
            Entity identifiers to keep.

        Returns
        -------
        ObsPeriodFilter
            Wrapping a new ObsPeriodPerEntity with only matching entities.
        """
        col      = self._obs.semantics.entity_id_col
        mask     = self._obs.data[col].isin(entity_ids)
        filtered = self._obs.data[mask].copy()
        obj = ObsPeriodPerEntity(
            filtered,
            self._obs.semantics,
            identity=self._obs.identity,
        )
        obj._construction_path = self._obs.construction_path + " (filtered)"
        return ObsPeriodFilter(obj)

    def by_dates(
        self,
        start:       str | pd.Timestamp | None = None,
        end:         str | pd.Timestamp | None = None,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "ObsPeriodFilter":
        """
        Keep only entities whose observation window falls within
        the given date range.

        Filters on obs_start against the start bound and obs_end
        against the end bound. This keeps entities whose entire
        window is contained within [start, end].

        Parameters
        ----------
        start : str | pd.Timestamp | None
            Lower bound — keep entities with obs_start >= start
            (or > if EXCLUSIVE). None means no lower bound.
        end : str | pd.Timestamp | None
            Upper bound — keep entities with obs_end <= end
            (or < if EXCLUSIVE). None means no upper bound.
        start_bound : DateBoundary
            INCLUSIVE (>=) or EXCLUSIVE (>). Default INCLUSIVE.
        end_bound : DateBoundary
            INCLUSIVE (<=) or EXCLUSIVE (<). Default INCLUSIVE.

        Returns
        -------
        ObsPeriodFilter
            Wrapping a new ObsPeriodPerEntity with only matching entities.

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

        sc  = self._obs.semantics.start_time_col
        ec  = self._obs.semantics.end_time_col
        df  = self._obs.data.copy()

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

        obj = ObsPeriodPerEntity(
            df,
            self._obs.semantics,
            identity=self._obs.identity,
        )
        obj._construction_path = self._obs.construction_path + " (filtered)"
        return ObsPeriodFilter(obj)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._obs)

    def __repr__(self) -> str:
        return (
            f"ObsPeriodFilter(\n"
            f"  obs_period : {self._obs!r}\n"
            f")"
        )
