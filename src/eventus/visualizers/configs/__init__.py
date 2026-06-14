"""
Public plotter configuration classes for eventus visualizers.

These are the user-facing config objects used to drive the plotters. Each is
also re-exported at the top level (``from eventus import StackedTimelineConfig``);
this module lets you import them from their natural location as well
(``from eventus.visualizers.configs import StackedTimelineConfig``).

Internal style/layout building-block configs are intentionally NOT re-exported
here, to keep the public surface small and stable.
"""

from .activity_over_time_config import ActivityOverTimeConfig
from .arrays_violin_config import ArraysViolinConfig
from .episode_duration_plot_config import EpisodeDurationPlotConfig
from .violin_config import EpisodeDurationViolinConfig
from .event_co_occurrence_directionality_plot_config import EventCoOccurrenceDirectionalityPlotConfig
from .event_co_occurrence_gap_plot_config import EventCoOccurrenceGapPlotConfig
from .event_result_shape_config import EventResultShapeConfig
from .event_result_timing_config import EventResultTimingConfig
from .event_result_volume_config import EventResultVolumeConfig
from .histogram_plot_config import HistogramPlotConfig
from .kde_plot_config import KDEPlotConfig
from .stacked_timeline_config import StackedTimelineConfig

__all__ = [
    "ActivityOverTimeConfig",
    "ArraysViolinConfig",
    "EpisodeDurationPlotConfig",
    "EpisodeDurationViolinConfig",
    "EventCoOccurrenceDirectionalityPlotConfig",
    "EventCoOccurrenceGapPlotConfig",
    "EventResultShapeConfig",
    "EventResultTimingConfig",
    "EventResultVolumeConfig",
    "HistogramPlotConfig",
    "KDEPlotConfig",
    "StackedTimelineConfig",
]
