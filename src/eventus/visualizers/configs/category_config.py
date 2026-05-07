"""
category_config.py

Defines CategoryConfig — a single category's visual identity (color + label) —
and parse_categories, a helper that builds a {key: CategoryConfig} dict from
a raw YAML-parsed mapping.

Used by:
    StratificationConfig  (histogram_plot_config.py)
    BaseViolinConfig      (violin_config.py)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eventus.visualizers.configs.plot_config_utils import err, validate_hex

_PREFIX = "CategoryConfig"


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class CategoryConfig:
    """Visual identity for one category: color and optional display label."""
    color: str
    label: str | None = None

    def __post_init__(self) -> None:
        validate_hex(self.color, "color", _PREFIX)


# ── Parse helper ──────────────────────────────────────────────────────────────

def parse_categories(raw: dict[str, Any] | None) -> dict[str, CategoryConfig]:
    """
    Build a {key: CategoryConfig} dict from a raw YAML-parsed mapping.

    Each value must be a dict with at least a 'color' key and an
    optional 'label' key.

    Parameters
    ----------
    raw : dict | None
        Raw mapping from YAML, e.g.:
            {"all_data": {"color": "#AAAAAA", "label": "All patients"},
             "H01":      {"color": "#028090"}}

    Returns
    -------
    dict[str, CategoryConfig]
        Empty dict if raw is None or empty.
    """
    if not raw:
        return {}
    out: dict[str, CategoryConfig] = {}
    for key, val in raw.items():
        if not isinstance(val, dict):
            raise err(
                _PREFIX,
                f"categories.{key!r} must be a mapping with 'color' and "
                f"optional 'label', got {type(val).__name__}",
            )
        valid = {"color", "label"}
        unknown = set(val.keys()) - valid
        if unknown:
            raise err(_PREFIX, f"unknown keys in categories.{key!r}: {sorted(unknown)}")
        out[key] = CategoryConfig(**val)
    return out
