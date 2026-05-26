"""
types.py
Shared types and enumerations for the eventus package.

Importable from the top level:
    from eventus import DateBoundary
    from eventus.types import DateBoundary
"""
from __future__ import annotations
from enum import Enum


class DateBoundary(Enum):
    """
    Controls whether a date boundary is inclusive or exclusive
    when filtering episodes, events, or observation periods.

    INCLUSIVE — the boundary date is included ( >= or <= )
    EXCLUSIVE — the boundary date is excluded ( >  or <  )

    Examples
    --------
    >>> from eventus.types import DateBoundary
    >>> EpisodesFilter(episodes).by_dates(
    ...     start       = "2022-01-01",
    ...     end         = "2022-12-31",
    ...     start_bound = DateBoundary.INCLUSIVE,
    ...     end_bound   = DateBoundary.EXCLUSIVE,
    ... )
    """
    INCLUSIVE = "inclusive"
    EXCLUSIVE = "exclusive"
