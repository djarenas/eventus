"""
episodes_filter.py
EpisodesFilter — filter a validated Episodes object by entities,
date ranges, or observation periods.

Filters are chainable — each method returns a new EpisodesFilter
wrapping the filtered Episodes, so calls can be composed in sequence.

The original Episodes object is never mutated.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.episodes import Episodes
from eventus.types import DateBoundary

_ERROR = "[EpisodesFilter] Error"

_DEFAULT_BOUND = DateBoundary.INCLUSIVE


class EpisodesFilter:
    """
    I filter a validated Episodes object. I am chainable.

    Each filter method returns a new EpisodesFilter so calls can
    be composed. Call .result to retrieve the filtered Episodes.

    Parameters
    ----------
    episodes : Episodes
        A validated Episodes object to filter.

    Examples
    --------
    >>> from eventus.cleaners import EpisodesFilter
    >>> from eventus.types import DateBoundary
    >>>
    >>> filtered = (
    ...     EpisodesFilter(episodes)
    ...     .by_entities(my_entity_ids)
    ...     .by_dates(start="2022-01-01", end="2022-12-31")
    ...     .result
    ... )
    >>>
    >>> # Filter to an observation period
    >>> filtered = (
    ...     EpisodesFilter(episodes)
    ...     .to_obs_period(obs, clip=True)
    ...     .result
    ... )
    """

    # ── Attributes ───────────────────────────────────────────────────────
    _episodes: Episodes  # the current filtered Episodes object

    def __init__(self, episodes: Episodes) -> None:
        if not isinstance(episodes, Episodes):
            raise TypeError(
                f"{_ERROR}: episodes must be an Episodes object, "
                f"got {type(episodes).__name__}"
            )
        self._episodes = episodes

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def result(self) -> Episodes:
        """Return the filtered Episodes object."""
        return self._episodes

    # ------------------------------------------------------------------ #
    # Filter methods
    # ------------------------------------------------------------------ #

    def by_entities(self, entity_ids) -> "EpisodesFilter":
        """
        Keep only episodes belonging to the specified entities.

        Parameters
        ----------
        entity_ids : list | set | pd.Series | np.ndarray
            Entity identifiers to keep.

        Returns
        -------
        EpisodesFilter
            Wrapping a new Episodes with only the matching rows.
        """
        col     = self._episodes.semantics.entity_id_col
        mask    = self._episodes.data[col].isin(entity_ids)
        filtered = self._episodes.data[mask].copy()
        return EpisodesFilter(
            Episodes._construct_from_cleaned(filtered, self._episodes.semantics)
        )

    def by_dates(
        self,
        start:       str | pd.Timestamp | None = None,
        end:         str | pd.Timestamp | None = None,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "EpisodesFilter":
        """
        Keep only episodes within the given date range.

        Filters on episode start date against the start bound and
        episode end date against the end bound.

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
        EpisodesFilter
            Wrapping a new Episodes with only the matching rows.

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

        sc  = self._episodes.semantics.start_time_col
        ec  = self._episodes.semantics.end_time_col
        df  = self._episodes.data.copy()

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

        return EpisodesFilter(
            Episodes._construct_from_cleaned(df, self._episodes.semantics)
        )

    def to_obs_period(
        self,
        obs_period,
        clip:        bool  = True,
        start_bound: DateBoundary = _DEFAULT_BOUND,
        end_bound:   DateBoundary = _DEFAULT_BOUND,
    ) -> "EpisodesFilter":
        """
        Filter episodes to each entity's observation period.

        Only entities present in obs_period are kept. Episodes outside
        the entity's obs window are dropped. Episodes that partially
        overlap the window are either clipped to the boundary or
        dropped entirely, controlled by the clip parameter.

        Parameters
        ----------
        obs_period : ObsPeriodPerEntity
            One row per entity defining the observation window.
            entity_id_col must match episodes.semantics.entity_id_col.
        clip : bool
            If True (default), episodes that partially overlap the obs
            window are clipped to the boundary.
            If False, episodes that partially overlap are dropped.
        start_bound : DateBoundary
            INCLUSIVE (>=) or EXCLUSIVE (>) for the obs_start boundary.
            Default INCLUSIVE.
        end_bound : DateBoundary
            INCLUSIVE (<=) or EXCLUSIVE (<) for the obs_end boundary.
            Default INCLUSIVE.

        Returns
        -------
        EpisodesFilter
            Wrapping a new Episodes filtered and optionally clipped
            to each entity's observation period.

        Raises
        ------
        ValueError
            If entity_id_col does not match between episodes and obs_period.
        """
        from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERROR} in to_obs_period(): obs_period must be an "
                f"ObsPeriodPerEntity object, got {type(obs_period).__name__}"
            )

        eps_entity_col = self._episodes.semantics.entity_id_col
        obs_entity_col = obs_period.semantics.entity_id_col

        if eps_entity_col != obs_entity_col:
            raise ValueError(
                f"{_ERROR} in to_obs_period(): entity_id_col mismatch. "
                f"Episodes has '{eps_entity_col}', "
                f"obs_period has '{obs_entity_col}'."
            )

        obs_start_col = obs_period.semantics.start_time_col
        obs_end_col   = obs_period.semantics.end_time_col
        eps_start_col = self._episodes.semantics.start_time_col
        eps_end_col   = self._episodes.semantics.end_time_col

        # Merge obs window onto episodes
        obs_lookup = obs_period.data.set_index(obs_entity_col)[
            [obs_start_col, obs_end_col]
        ].rename(columns={
            obs_start_col: "_obs_start",
            obs_end_col:   "_obs_end",
        })

        df = self._episodes.data.merge(
            obs_lookup,
            left_on  = eps_entity_col,
            right_index = True,
            how      = "inner",  # drops entities not in obs_period
        )

        # Apply start bound
        if start_bound == DateBoundary.INCLUSIVE:
            overlaps_start = df[eps_end_col] >= df["_obs_start"]
        else:
            overlaps_start = df[eps_end_col] > df["_obs_start"]

        # Apply end bound
        if end_bound == DateBoundary.INCLUSIVE:
            overlaps_end = df[eps_start_col] <= df["_obs_end"]
        else:
            overlaps_end = df[eps_start_col] < df["_obs_end"]

        if clip:
            # Keep overlapping episodes and clip to obs boundaries
            df = df[overlaps_start & overlaps_end].copy()
            if start_bound == DateBoundary.INCLUSIVE:
                df[eps_start_col] = df[[eps_start_col, "_obs_start"]].max(axis=1)
            else:
                df[eps_start_col] = df[[eps_start_col, "_obs_start"]].max(axis=1)
            if end_bound == DateBoundary.INCLUSIVE:
                df[eps_end_col] = df[[eps_end_col, "_obs_end"]].min(axis=1)
            else:
                df[eps_end_col] = df[[eps_end_col, "_obs_end"]].min(axis=1)
        else:
            # Drop episodes that partially overlap — keep only fully contained
            if start_bound == DateBoundary.INCLUSIVE:
                fully_inside_start = df[eps_start_col] >= df["_obs_start"]
            else:
                fully_inside_start = df[eps_start_col] > df["_obs_start"]

            if end_bound == DateBoundary.INCLUSIVE:
                fully_inside_end = df[eps_end_col] <= df["_obs_end"]
            else:
                fully_inside_end = df[eps_end_col] < df["_obs_end"]

            df = df[fully_inside_start & fully_inside_end].copy()

        df = df.drop(columns=["_obs_start", "_obs_end"]).reset_index(drop=True)

        return EpisodesFilter(
            Episodes._construct_from_cleaned(df, self._episodes.semantics)
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._episodes)

    def __repr__(self) -> str:
        return (
            f"EpisodesFilter(\n"
            f"  episodes : {self._episodes!r}\n"
            f")"
        )
