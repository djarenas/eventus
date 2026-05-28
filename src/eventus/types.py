"""
types.py
Shared types and enumerations for the eventus package.

Importable from the top level:
    from eventus import DateBoundary
    from eventus import EpisodeCoverageMetric
    from eventus.types import DateBoundary
    from eventus.types import EpisodeCoverageMetric
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


class EpisodeCoverageMetric(str, Enum):
    """
    Metrics produced by CohortTimelineEpisodeAnalyzer.enrich_with_episode_coverage().

    Each value corresponds to the suffix of an eps_comp_{identity}_{metric}
    column in a CohortTimeline. Using str, Enum means values compare equal
    to their string equivalents — column name construction works without
    any conversion:

        f"eps_comp_{identity}_{EpisodeCoverageMetric.ACTIVE_DAYS}"
        → "eps_comp_inpatient_hospitalization_active_days"

    Numeric metrics (day counts):
        ACTIVE_DAYS                        — days covered by episodes
        INACTIVE_DAYS                      — days not covered
        INACTIVE_DAYS_BEFORE_FIRST_EPISODE — gap before first episode
        INACTIVE_DAYS_AFTER_LAST_EPISODE   — gap after last episode
        INACTIVE_DAYS_MIDDLE               — sum of gaps between episodes

    Date metrics:
        FIRST_START — date of first episode start within obs period
        LAST_END    — date of last episode end within obs period

    Examples
    --------
    >>> from eventus.types import EpisodeCoverageMetric
    >>> plotter = StackedTimelinePlotter(
    ...     cohort_timeline,
    ...     config,
    ...     sort_identity = "inpatient_hospitalization",
    ...     sort_metrics  = [EpisodeCoverageMetric.ACTIVE_DAYS],
    ...     ascending     = False,
    ... )
    """
    ACTIVE_DAYS                        = "active_days"
    INACTIVE_DAYS                      = "inactive_days"
    INACTIVE_DAYS_BEFORE_FIRST_EPISODE = "inactive_days_before_first_episode"
    INACTIVE_DAYS_AFTER_LAST_EPISODE   = "inactive_days_after_last_episode"
    INACTIVE_DAYS_MIDDLE               = "inactive_days_middle"
    FIRST_START                        = "first_start"
    LAST_END                           = "last_end"
