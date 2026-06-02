"""
arrays_violin_plotter_utils.py
Drawing utilities for ArraysViolinPlotter.

Shared violin primitives (compute_widths, draw_violin_body, draw_box,
draw_points, draw_percentile_lines, apply_y_bounds, build_tick_labels)
now live in eventus.visualizers.violin_utils.

This module re-exports those shared functions and adds
ArraysViolinPlotter-specific logic only.
"""
from __future__ import annotations

# ── Re-exports from violin_utils ──────────────────────────────────────────────

from eventus.visualizers.violins.violin_utils import (
    apply_y_bounds,
    build_tick_labels,
    compute_widths,
    draw_box,
    draw_percentile_lines,
    draw_points,
    draw_violin_body,
)

__all__ = [
    "apply_y_bounds",
    "build_tick_labels",
    "compute_widths",
    "draw_box",
    "draw_percentile_lines",
    "draw_points",
    "draw_violin_body",
]
