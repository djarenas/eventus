"""
eventus
=======
A domain-agnostic Python framework for analyzing entities that
experience episodes within defined observation periods.

Quick start
-----------
>>> from eventus import (
...     EpisodeSemantics, EventSemantics,
...     Episodes, Events, ObsPeriodPerEntity,
...     EpisodesCleaner, EpisodesCleanerConfig,
...     EventsCleaner, EventsCleanerConfig,
...     EpisodesFilter, EventsFilter, ObsPeriodFilter,
...     CohortTimeline,
...     CohortTimelineEpisodeAnalyzer,
...     CohortTimelineEventAnalyzer,
...     EpisodeDurationAnalyzer,
...     DateBoundary,
...     EpisodeCoverageMetric,
...     EventCoOccurrenceAnalyzer,
... )

Submodule imports also work:
>>> from eventus.data_objects import Episodes
>>> from eventus.semantics import EpisodeSemantics
>>> from eventus.intermediates import CohortTimeline
>>> from eventus.analyzers import CohortTimelineEventAnalyzer
"""

# ── Types ─────────────────────────────────────────────────────────────────────
from eventus.types import DateBoundary
from eventus.types import EpisodeCoverageMetric

# ── Semantics ─────────────────────────────────────────────────────────────────
from eventus.semantics.episode_semantics import EpisodeSemantics
from eventus.semantics.event_semantics import EventSemantics

# ── Data objects ──────────────────────────────────────────────────────────────
from eventus.data_objects.episodes import Episodes
from eventus.data_objects.episodes_per_entity import EpisodesPerEntity
from eventus.data_objects.events import Events
from eventus.data_objects.events_per_entity import EventsPerEntity
from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

# ── Cleaners ──────────────────────────────────────────────────────────────────
from eventus.cleaners.episodes_cleaner import EpisodesCleaner
from eventus.cleaners.episodes_cleaner_config import EpisodesCleanerConfig
from eventus.cleaners.episodes_filter import EpisodesFilter
from eventus.cleaners.events_cleaner import EventsCleaner
from eventus.cleaners.events_cleaner_config import EventsCleanerConfig
from eventus.cleaners.events_filter import EventsFilter
from eventus.cleaners.obs_period_filter import ObsPeriodFilter

# ── Analyzers ─────────────────────────────────────────────────────────────────
from eventus.analyzers.cohort_timeline_episode_analyzer import CohortTimelineEpisodeAnalyzer
from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
from eventus.analyzers.episode_duration_analyzer import EpisodeDurationAnalyzer
from eventus.analyzers.event_episode_analyzer import EventEpisodeAnalyzer
from eventus.analyzers.event_co_occurrence_analyzer import EventCoOccurrenceAnalyzer

# ── Intermediates ─────────────────────────────────────────────────────────────
from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.episode_activity_over_time import EpisodeActivityOverTime
from eventus.intermediates.episode_coverage_summary import EpisodeCoverageSummary
from eventus.intermediates.episode_duration_result import EpisodeDurationResult
from eventus.intermediates.event_episode_result import EventEpisodeResult
from eventus.intermediates.event_result_volume import EventResultVolume
from eventus.intermediates.event_result_timing import EventResultTiming
from eventus.intermediates.event_result_shape import EventResultShape
from eventus.intermediates.survival_result import SurvivalResult
from eventus.intermediates.event_co_occurrence_result import EventCoOccurrenceResult
from eventus.intermediates.event_co_occurrence_presence_result import EventCoOccurrencePresenceResult
from eventus.intermediates.event_co_occurrence_gap_result import EventCoOccurrenceGapResult
from eventus.intermediates.event_co_occurrence_association import EventCoOccurrenceAssociation

# ── Visualizer configs ────────────────────────────────────────────────────────
from eventus.visualizers.configs.activity_over_time_config import ActivityOverTimeConfig
from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
from eventus.visualizers.configs.episode_duration_plot_config import EpisodeDurationPlotConfig
from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.configs.kde_plot_config import KDEPlotConfig
from eventus.visualizers.configs.event_result_shape_config import EventResultShapeConfig
from eventus.visualizers.configs.event_result_timing_config import EventResultTimingConfig
from eventus.visualizers.configs.event_result_volume_config import EventResultVolumeConfig
from eventus.visualizers.configs.stacked_timeline_config import StackedTimelineConfig
from eventus.visualizers.configs.violin_config import EpisodeDurationViolinConfig

# ── Visualizers ───────────────────────────────────────────────────────────────
from eventus.visualizers.activity_over_time_plotter import ActivityOverTimePlotter
from eventus.visualizers.episode_duration_histogram_plotter import EpisodeDurationHistogramPlotter
from eventus.visualizers.stacked_timeline_plotter import StackedTimelinePlotter

# ── Visualizers — events ─────────────────────────────────────────────────
from eventus.visualizers.events.event_result_shape_plotter import EventResultShapePlotter
from eventus.visualizers.events.event_result_timing_plotter import EventResultTimingPlotter
from eventus.visualizers.events.event_result_volume_plotter import EventResultVolumePlotter

# ── Visualizers — violins ─────────────────────────────────────────────────────
from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter
from eventus.visualizers.violins.episode_coverage_violin_plotter import EpisodeCoverageViolinPlotter
from eventus.visualizers.violins.episode_duration_violin_plotter import EpisodeDurationViolinPlotter

__version__ = "0.1.0"

__all__ = [
    # Types
    "DateBoundary",
    "EpisodeCoverageMetric",

    # Semantics
    "EpisodeSemantics",
    "EventSemantics",

    # Data objects
    "Episodes",
    "EpisodesPerEntity",
    "Events",
    "EventsPerEntity",
    "ObsPeriodPerEntity",

    # Cleaners
    "EpisodesCleaner",
    "EpisodesCleanerConfig",
    "EpisodesFilter",
    "EventsCleaner",
    "EventsCleanerConfig",
    "EventsFilter",
    "ObsPeriodFilter",

    # Analyzers
    "CohortTimelineEpisodeAnalyzer",
    "CohortTimelineEventAnalyzer",
    "EpisodeDurationAnalyzer",
    "EventEpisodeAnalyzer",
    "EventCoOccurrenceAnalyzer",

    # Intermediates
    "CohortTimeline",
    "EpisodeActivityOverTime",
    "EpisodeCoverageSummary",
    "EpisodeDurationResult",
    "EventEpisodeResult",
    "EventResultVolume",
    "EventResultTiming",
    "EventResultShape",
    "SurvivalResult",
    "EventCoOccurrenceResult",
    "EventCoOccurrencePresenceResult",
    "EventCoOccurrenceGapResult",
    "EventCoOccurrenceAssociation",

    # Visualizer configs
    "ActivityOverTimeConfig",
    "ArraysViolinConfig",
    "EpisodeDurationPlotConfig",
    "HistogramPlotConfig",
    "KDEPlotConfig",
    "EventResultShapeConfig",
    "EventResultTimingConfig",
    "EventResultVolumeConfig",
    "StackedTimelineConfig",
    "EpisodeDurationViolinConfig",

    # Visualizers
    "ActivityOverTimePlotter",
    "EpisodeDurationHistogramPlotter",
    "StackedTimelinePlotter",

    # Visualizers — events
    "EventResultShapePlotter",
    "EventResultTimingPlotter",
    "EventResultVolumePlotter",

    # Visualizers — violins
    "ArraysViolinPlotter",
    "EpisodeCoverageViolinPlotter",
    "EpisodeDurationViolinPlotter",
]
