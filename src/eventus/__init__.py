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
from eventus.semantics.descriptor_col_config import DescriptorColConfig

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
from eventus.analyzers.episode_event_interaction_analyzer import EpisodeEventInteractionAnalyzer
from eventus.analyzers.event_cooccurrence.event_co_occurrence_analyzer import EventCoOccurrenceAnalyzer
from eventus.analyzers.event_cooccurrence.event_co_occurrence_gap_analyzer import EventCoOccurrenceGapAnalyzer
from eventus.analyzers.event_cooccurrence.event_co_occurrence_directionality_analyzer import EventCoOccurrenceDirectionalityAnalyzer

# ── Intermediates ─────────────────────────────────────────────────────────────
from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.episode_activity_over_time import EpisodeActivityOverTime
from eventus.intermediates.episode_duration_result import EpisodeDurationResult
from eventus.intermediates.episode_coverage_summary import EpisodeCoverageSummary
from eventus.intermediates.episode_event_interaction_result import EpisodeEventInteractionResult
from eventus.intermediates.event_result_volume import EventResultVolume
from eventus.intermediates.event_result_timing import EventResultTiming
from eventus.intermediates.event_result_shape import EventResultShape
from eventus.intermediates.event_cooccurrence.event_co_occurrence_result import EventCoOccurrenceResult
from eventus.intermediates.event_cooccurrence.event_co_occurrence_presence_result import EventCoOccurrencePresenceResult
from eventus.intermediates.event_cooccurrence.event_co_occurrence_association import EventCoOccurrenceAssociation
from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_summary import EventCoOccurrenceGapSummary
from eventus.intermediates.event_cooccurrence.event_co_occurrence_gap_test import EventCoOccurrenceGapTest
from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_summary import EventCoOccurrenceDirectionalitySummary
from eventus.intermediates.event_cooccurrence.event_co_occurrence_directionality_test import EventCoOccurrenceDirectionalityTest

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
from eventus.visualizers.configs.event_co_occurrence_gap_plot_config import EventCoOccurrenceGapPlotConfig
from eventus.visualizers.configs.event_co_occurrence_directionality_plot_config import EventCoOccurrenceDirectionalityPlotConfig

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

from importlib.metadata import version as _version
__version__ = _version("eventus")

__all__ = [
    # Types
    "DateBoundary",
    "EpisodeCoverageMetric",

    # Semantics
    "EpisodeSemantics",
    "EventSemantics",
    "DescriptorColConfig",

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
    "EpisodeEventInteractionAnalyzer",
    "EventCoOccurrenceAnalyzer",
    "EventCoOccurrenceGapAnalyzer",
    "EventCoOccurrenceDirectionalityAnalyzer",

    # Intermediates
    "CohortTimeline",
    "EpisodeActivityOverTime",
    "EpisodeCoverageSummary",
    "EpisodeDurationResult",
    "EpisodeEventInteractionResult",
    "EventResultVolume",
    "EventResultTiming",
    "EventResultShape",
    "EventCoOccurrenceResult",
    "EventCoOccurrencePresenceResult",
    "EventCoOccurrenceAssociation",
    "EventCoOccurrenceGapSummary",
    "EventCoOccurrenceGapTest",
    "EventCoOccurrenceDirectionalitySummary",
    "EventCoOccurrenceDirectionalityTest",

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
    "EventCoOccurrenceGapPlotConfig",
    "EventCoOccurrenceDirectionalityPlotConfig",

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
