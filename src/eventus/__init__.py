"""
eventus
=======
A domain-agnostic Python framework for analyzing entities that
experience events within defined observation periods.

Quick start
-----------
>>> from eventus import (
...     EventSemantics, Events, EventsCleaner, EventsCleanerConfig,
...     ObsPeriodPerEntity, EventsWithinObsPeriodsAnalyzer,
... )

Submodule imports also work:
>>> from eventus.data_objects import Events
>>> from eventus.semantics import EventSemantics
"""

# Semantics
from eventus.semantics.event_semantics import EventSemantics
from eventus.semantics.occurrence_semantics import OccurrenceSemantics

# Data objects
from eventus.data_objects.events import Events
from eventus.data_objects.events_per_entity import EventsPerEntity
from eventus.data_objects.occurrences import Occurrences
from eventus.data_objects.occurrences_per_entity import OccurrencesPerEntity
from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

# Cleaners
from eventus.cleaners.events_cleaner import EventsCleaner
from eventus.cleaners.events_cleaner_config import EventsCleanerConfig
from eventus.cleaners.occurrences_cleaner import OccurrencesCleaner
from eventus.cleaners.occurrences_cleaner_config import OccurrencesCleanerConfig

# Analyzers
from eventus.analyzers.event_duration_analyzer import EventDurationAnalyzer
from eventus.analyzers.cohort_timeline_event_analyzer import CohortTimelineEventAnalyzer
from eventus.analyzers.cohort_timeline_occurrence_analyzer import CohortTimelineOccurrenceAnalyzer

# Cohort Timeline
from eventus.cohort_timeline.cohort_timeline import CohortTimeline

# Visualizers
from eventus.visualizers.activity_over_time_config import ActivityOverTimeConfig
from eventus.visualizers.activity_over_time_plotter import ActivityOverTimePlotter
from eventus.visualizers.events_duration_plotter import EventsDurationPlotter
from eventus.visualizers.histogram_config import HistogramConfig
from eventus.visualizers.stacked_timeline_config import StackedTimelineConfig
from eventus.visualizers.stacked_timeline_plotter import StackedTimelinePlotter

# Violin visualizers
from eventus.visualizers.violins.base_violin_config import BaseViolinConfig
from eventus.visualizers.violins.event_duration_violin_config import EventDurationViolinConfig
from eventus.visualizers.violins.events_duration_violin_plotter import EventsDurationViolinPlotter
from eventus.visualizers.violins.event_coverage_violin_config import EventCoverageViolinConfig
from eventus.visualizers.violins.event_coverage_violin_plotter import EventCoverageViolinPlotter

__version__ = "0.1.0"

__all__ = [
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
    "OccurrencesCleaner",
    "OccurrencesCleanerConfig",
    # Analyzers
    "EventDurationAnalyzer",
    "EventsWithinObsPeriodsAnalyzer",
    "OccurrencesWithinObsPeriodsAnalyzer",
    # Pipe-delimited format
    "PipeDelimitedFormat",
    "PipeDelimitedFormatEvents",
    "PipeDelimitedFormatOccurrences",
    # Visualizers
    "ActivityOverTimeConfig",
    "ActivityOverTimePlotter",
    "EventsDurationPlotter",
    "HistogramConfig",
    "StackedTimelineConfig",
    "StackedTimelinePlotter",
    # Violin visualizers
    "BaseViolinConfig",
    "EventDurationViolinConfig",
    "EventsDurationViolinPlotter",
    "EventCoverageViolinConfig",
    "EventCoverageViolinPlotter",

]
