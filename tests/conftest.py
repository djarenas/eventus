"""Shared pytest fixtures for eventus vignette-pinned smoke tests.

These tests run the real analytical pipeline on the bundled vignette data
and assert the exact numbers reported in the manuscript and README. They
are integration smoke tests: their job is to catch regressions where a
change silently shifts a published result.

All tests are skipped automatically if the vignette data directory is not
present (e.g. in a minimal install that excludes vignettes), so the suite
never fails for the wrong reason.
"""
from __future__ import annotations

import pathlib

import pytest

# ---------------------------------------------------------------------------
# Locate the vignette assets relative to the repo root.
# tests/ lives at <repo>/tests, vignettes at <repo>/vignettes.
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VIGNETTES = REPO_ROOT / "vignettes"
DATA = VIGNETTES / "data"


def _require(path: pathlib.Path) -> pathlib.Path:
    """Skip the test cleanly if a required vignette asset is missing."""
    if not path.exists():
        pytest.skip(f"vignette asset not found: {path.relative_to(REPO_ROOT)}")
    return path


@pytest.fixture(scope="session")
def vignettes_dir() -> pathlib.Path:
    return _require(VIGNETTES)


@pytest.fixture(scope="session")
def data_dir() -> pathlib.Path:
    return _require(DATA)


@pytest.fixture
def asset(vignettes_dir):
    """Return a helper that resolves (and existence-checks) a vignette asset."""
    def _resolve(*parts: str) -> pathlib.Path:
        return _require(vignettes_dir.joinpath(*parts))
    return _resolve
