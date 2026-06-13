"""Import-level smoke tests: the package loads and its advertised public
API is actually importable. These guard against broken __init__ exports
(e.g. a name listed in __all__ but never imported).
"""
from __future__ import annotations

import importlib

import pytest

import eventus


def test_version_present():
    assert isinstance(eventus.__version__, str)
    assert eventus.__version__  # non-empty


@pytest.mark.parametrize("name", eventus.__all__)
def test_all_names_are_importable(name):
    """Every name in __all__ must resolve as a real attribute."""
    assert hasattr(eventus, name), f"{name} is in __all__ but not importable"


def test_star_import_succeeds():
    namespace: dict = {}
    exec("from eventus import *", namespace)
    exported = [k for k in namespace if not k.startswith("__")]
    assert len(exported) == len(eventus.__all__)


@pytest.mark.parametrize(
    "subpackage",
    [
        "eventus.semantics",
        "eventus.data_objects",
        "eventus.cleaners",
        "eventus.analyzers",
        "eventus.intermediates",
        "eventus.visualizers",
        "eventus.types",
    ],
)
def test_subpackages_import(subpackage):
    importlib.import_module(subpackage)


def test_readme_quickstart_names_exist():
    """Names used verbatim in the README quickstart must be top-level."""
    for name in (
        "EpisodeSemantics",
        "EventSemantics",
        "DescriptorColConfig",
        "Episodes",
        "EpisodesCleaner",
        "EpisodesCleanerConfig",
        "CohortTimeline",
        "CohortTimelineEpisodeAnalyzer",
        "StackedTimelineConfig",
        "StackedTimelinePlotter",
        "EventCoOccurrenceAnalyzer",
        "EventCoOccurrenceGapAnalyzer",
        "EventCoOccurrenceDirectionalityAnalyzer",
    ):
        assert hasattr(eventus, name), f"README references eventus.{name} but it is not exported"
