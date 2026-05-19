"""
eventus
=======
A domain-agnostic Python framework for analyzing entities that
experience events within defined observation periods.

Quick start
-----------
>>> from eventus import (
...     EventSemantics, OccurrenceSemantics,
...     Events, Occurrences, ObsPeriodPerEntity,
...     EventsCleaner, EventsCleanerConfig,
...     OccurrencesCleaner, OccurrencesCleanerConfig,
...     EventsFilter, OccurrencesFilter, ObsPeriodFilter,
...     CohortTimeline,
...     CohortTimelineEventAnalyzer,
...     CohortTimelineOccurrenceAnalyzer,
...     EventDurationAnalyzer,
...     DateBoundary,
... )

Submodule imports also work:
>>> from eventus.data_objects import Events
>>> from eventus.semantics import EventSemantics
>>> from eventus.intermediates import CohortTimeline
>>> from eventus.analyzers import CohortTimelineOccurrenceAnalyzer
"""

# ── Types ─────────────────────────────────────────────────────────────────────
from eventus.types import DateBoundary

# ── Semantics ─────────────────────────────────────────────────────────────────
from eventus.semantics.event_semantics import EventSemantics
from eventus.semantics.occurrence_semantics import OccurrenceSemantics

# ── Data objects ──────────────────────────────────────────────────────────────
from eventus.data_objects.events import Events
from eventus.data_objects.events_per_entity import EventsPerEntity
from eventus.data_objects.occurrences import Occurrences
from eventus.data_objects.occurrences_per_entity import OccurrencesPerEntity
from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

# ── Cleaners ──────────────────────────────────────────────────────────────────
from eventus.cleaners.events_cleaner import EventsCleaner
from eventus.cleaners.events_cleaner_config import EventsCleanerConfig
from eventus.cleaners.events_filter import EventsFilter
from eventus.cleaners.occurrences_cleaner import OccurrencesCleaner
from eventus.cleaners.occurrences_cleaner_config import OccurrencesCleanerConfig
from eventus.cleaners.occurrences_filter import OccurrencesFilter
from eventus.cleaners.obs_period_filter import ObsPeriodFilter

# ── Analyzers ─────────────────────────────────────────────────────────────────
from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
from eventus.analyzers.cohort_timeline_occurrence_analyzer import CohortTimelineOccurrenceAnalyzer
from eventus.analyzers.event_duration_analyzer import EventDurationAnalyzer
from eventus.analyzers.occurrence_event_analyzer import OccurrenceEventAnalyzer

# ── Intermediates ─────────────────────────────────────────────────────────────
from eventus.intermediates.cohort_timeline import CohortTimeline
from eventus.intermediates.event_activity_over_time import EventActivityOverTime
from eventus.intermediates.event_coverage_summary import EventCoverageSummary
from eventus.intermediates.event_duration_result import EventDurationResult
from eventus.intermediates.occurrence_event_result import OccurrenceEventResult
from eventus.intermediates.occurrence_result_volume import OccurrenceResultVolume
from eventus.intermediates.occurrence_result_timing import OccurrenceResultTiming
from eventus.intermediates.occurrence_result_shape import OccurrenceResultShape
from eventus.intermediates.survival_result import SurvivalResult

# ── Visualizer configs ────────────────────────────────────────────────────────
from eventus.visualizers.configs.activity_over_time_config import ActivityOverTimeConfig
from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
from eventus.visualizers.configs.event_duration_plot_config import EventDurationPlotConfig
from eventus.visualizers.configs.histogram_plot_config import HistogramPlotConfig
from eventus.visualizers.configs.kde_plot_config import KDEPlotConfig
from eventus.visualizers.configs.occurrence_result_shape_config import OccurrenceResultShapeConfig
from eventus.visualizers.configs.occurrence_result_timing_config import OccurrenceResultTimingConfig
from eventus.visualizers.configs.occurrence_result_volume_config import OccurrenceResultVolumeConfig
from eventus.visualizers.configs.stacked_timeline_config import StackedTimelineConfig

# ── Visualizers ───────────────────────────────────────────────────────────────
from eventus.visualizers.activity_over_time_plotter import ActivityOverTimePlotter
from eventus.visualizers.event_duration_histogram_plotter import EventDurationHistogramPlotter
from eventus.visualizers.stacked_timeline_plotter import StackedTimelinePlotter

# ── Visualizers — occurrences ─────────────────────────────────────────────────
from eventus.visualizers.occurrences.occurrence_result_shape_plotter import OccurrenceResultShapePlotter
from eventus.visualizers.occurrences.occurrence_result_timing_plotter import OccurrenceResultTimingPlotter
from eventus.visualizers.occurrences.occurrence_result_volume_plotter import OccurrenceResultVolumePlotter

# ── Visualizers — violins ─────────────────────────────────────────────────────
from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter
from eventus.visualizers.violins.event_coverage_violin_plotter import EventCoverageViolinPlotter
from eventus.visualizers.violins.event_duration_violin_plotter import EventDurationViolinPlotter

__version__ = "0.1.0"

__all__ = [
    # Types
    "DateBoundary",

    # Semantics
    "EventSemantics",
    "OccurrenceSemantics",

    # Data objects
    "Events",
    "EventsPerEntity",
    "Occurrences",
    "OccurrencesPerEntity",
    "ObsPeriodPerEntity",

    # Cleaners
    "EventsCleaner",
    "EventsCleanerConfig",
    "EventsFilter",
    "OccurrencesCleaner",
    "OccurrencesCleanerConfig",
    "OccurrencesFilter",
    "ObsPeriodFilter",

    # Analyzers
    "CohortTimelineEventAnalyzer",
    "CohortTimelineOccurrenceAnalyzer",
    "EventDurationAnalyzer",
    "OccurrenceEventAnalyzer",

    # Intermediates
    "CohortTimeline",
    "EventActivityOverTime",
    "EventCoverageSummary",
    "EventDurationResult",
    "OccurrenceEventResult",
    "OccurrenceResultVolume",
    "OccurrenceResultTiming",
    "OccurrenceResultShape",
    "SurvivalResult",

    # Visualizer configs
    "ActivityOverTimeConfig",
    "ArraysViolinConfig",
    "EventDurationPlotConfig",
    "HistogramPlotConfig",
    "KDEPlotConfig",
    "OccurrenceResultShapeConfig",
    "OccurrenceResultTimingConfig",
    "OccurrenceResultVolumeConfig",
    "StackedTimelineConfig",

    # Visualizers
    "ActivityOverTimePlotter",
    "EventDurationHistogramPlotter",
    "StackedTimelinePlotter",

    # Visualizers — occurrences
    "OccurrenceResultShapePlotter",
    "OccurrenceResultTimingPlotter",
    "OccurrenceResultVolumePlotter",

    # Visualizers — violins
    "ArraysViolinPlotter",
    "EventCoverageViolinPlotter",
    "EventDurationViolinPlotter",
]
