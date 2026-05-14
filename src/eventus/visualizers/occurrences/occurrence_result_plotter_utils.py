"""
occurrence_result_plotter_utils.py
Occurrence-specific drawing utilities for occurrence result plotters.

Shared primitives (validate_path, save_figure, apply_style,
compute_bins, draw_histogram, draw_percentile_lines, resolve_x_limits)
now live in:
    eventus.visualizers.plot_utils       — universal primitives
    eventus.visualizers.histogram_utils  — histogram/distribution primitives

This module re-exports those shared functions for backwards compatibility
within the occurrences subfolder, and adds occurrence-specific logic only.
"""
from __future__ import annotations

# ── Re-exports from shared utils ──────────────────────────────────────────────
# Occurrence plotters import from here — they don't need to know where
# the implementation lives.

from eventus.visualizers.plot_utils import (
    validate_path,
    save_figure,
    apply_style,
)
from eventus.visualizers.histogram_utils import (
    compute_bins,
    draw_histogram,
    draw_percentile_lines,
    resolve_x_limits,
)

__all__ = [
    "validate_path",
    "save_figure",
    "apply_style",
    "compute_bins",
    "draw_histogram",
    "draw_percentile_lines",
    "resolve_x_limits",
]
