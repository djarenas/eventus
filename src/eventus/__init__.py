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

# Intermediates
from eventus.intermediates.cohort_timeline import CohortTimeline

# Visualizers
from eventus.visualizers.activity_over_time_plotter import ActivityOverTimePlotter
from eventus.visualizers.events_duration_plotter import EventsDurationPlotter
from eventus.visualizers.stacked_timeline_plotter import StackedTimelinePlotter

# Configuration objects for visualizers
from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
from eventus.visualizers.configs.stacked_timeline_config import StackedTimelineConfig
from eventus.visualizers.configs.activity_over_time_config import ActivityOverTimeConfig

# Violins
from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter
from eventus.visualizers.violins.event_coverage_violin_plotter import EventCoverageViolinPlotter 


# # Occurrences result visualizers
# from eventus.visualizers.occurrences.occurrence_result_plotter_config import (
#     OccurrenceResultVolumeConfig, 
#     OccurrenceResultTimingConfig, 
#     OccurrenceResultShapeConfig)
# from eventus.visualizers.occurrences.occurrence_result_shape_plotter import OccurrenceResultShapePlotter
# from eventus.visualizers.occurrences.occurrence_result_timing_plotter import OccurrenceResultTimingPlotter
# from eventus.visualizers.occurrences.occurrence_result_volume_plotter import OccurrenceResultVolumePlotter


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
    # Intermediates
    "CohortTimeline",
    "EventActivityOverTime",
    
    # Visualizers
    
    "ActivityOverTimePlotter",
    "EventsDurationPlotter",
    "StackedTimelineConfig",
    "StackedTimelinePlotter",
    
    # Visualizer Configs
    "ArraysViolinConfig",
    "StackedTimelineConfig",
    "ActivityOverTimeConfig",
    
    # Violin visualizers
    "ArraysViolinPlotter",
    "EventCoverageViolinPlotter"

    # # OccurrenceResults visualizers
    # "OccurrenceResultPlotterConfig",
    # "OccurrenceResultPlotterConfig", 
    # "OccurrenceResultVolumeConfig", 
    # "OccurrenceResultTimingConfig", 
    # "OccurrenceResultShapeConfig",
    # "OccurrenceResultShapePlotter",
    # "OccurrenceResultTimingPlotter",
    # "OccurrenceResultVolumePlotter"
]
