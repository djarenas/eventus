"""
events_cleaner_config.py
Configuration dataclass for EventsCleaner.
Controls what counts as a valid row for a given events dataset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import yaml

from eventus.cleaners.event_consolidate_config import EventConsolidateConfig

_ERROR_PREFIX = "[EventsCleanerConfig] Error"


@dataclass
class EventsCleanerConfig:
    """
    I am a reproducible set of rules for what counts as a valid
    event row. I can be built from a YAML file and saved back
    to one.

    Parameters
    ----------
    normalize_dates : bool
        Strip time components — keep dates only. Default True.

    parse_dates : bool
        Auto-parse date column from strings. Default True.

    drop_duplicates : bool
        Remove rows identical across entity_id, date, and
        also_defined_by columns. Default True.

    consolidate : EventConsolidateConfig | None
        Consolidate same-date records sharing the same entity and
        also_defined_by values into one event, aggregating
        descriptor columns according to declared rules.
        None (default) — no consolidation beyond deduplication.

    date_floor : str
        Reject rows with date before this value. Default "1920-01-01".

    date_ceiling : str
        Reject rows with date after this value. Default "2100-01-01".

    Example YAML
    ------------
    normalize_dates: true
    parse_dates:     true
    drop_duplicates: true
    date_floor:      "1920-01-01"
    date_ceiling:    "2030-01-01"

    consolidate:
      descriptor_cols:
        triage_level:   unique
        wait_time_mins: median
    """

    normalize_dates:      bool                               = True
    parse_dates:          bool                               = True
    drop_duplicate_rows:  bool                               = True
    consolidate:          EventConsolidateConfig | None = None
    date_floor:           str                                = "1920-01-01"
    date_ceiling:         str                                = "2100-01-01"

    def __post_init__(self) -> None:
        if self.consolidate is not None and \
                not isinstance(self.consolidate, EventConsolidateConfig):
            raise ValueError(
                f"{_ERROR_PREFIX}: consolidate must be an "
                f"EventConsolidateConfig or None, "
                f"got {type(self.consolidate).__name__}"
            )
        try:
            floor   = pd.Timestamp(self.date_floor)
            ceiling = pd.Timestamp(self.date_ceiling)
        except Exception as e:
            raise ValueError(
                f"{_ERROR_PREFIX}: invalid date_floor or date_ceiling: {e}"
            )
        if floor >= ceiling:
            raise ValueError(
                f"{_ERROR_PREFIX}: date_floor ({self.date_floor}) must be "
                f"before date_ceiling ({self.date_ceiling})"
            )

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_from_yaml(cls, path) -> "EventsCleanerConfig":
        """
        Build an EventsCleanerConfig from a YAML file.

        Parameters
        ----------
        path : str | pathlib.Path
        """
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)

        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML file must be a mapping, "
                f"got {type(cfg).__name__}"
            )

        known_keys = {
            "normalize_dates", "parse_dates", "drop_duplicate_rows",
            "consolidate", "date_floor", "date_ceiling",
        }
        unknown = set(cfg.keys()) - known_keys
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown keys in YAML: {sorted(unknown)}. "
                f"Valid keys: {sorted(known_keys)}"
            )

        consolidate_data = cfg.pop("consolidate", None)
        consolidate = (
            EventConsolidateConfig.from_dict(consolidate_data)
            if consolidate_data else None
        )

        return cls(**cfg, consolidate=consolidate)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def to_yaml(self, path) -> None:
        """Save this config to a YAML file."""
        cfg: dict[str, Any] = {
            "normalize_dates":     self.normalize_dates,
            "parse_dates":         self.parse_dates,
            "drop_duplicate_rows": self.drop_duplicate_rows,
            "date_floor":          self.date_floor,
            "date_ceiling":        self.date_ceiling,
        }
        if self.consolidate is not None:
            cfg["consolidate"] = {
                "descriptor_cols": self.consolidate.descriptor_cols
            }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)

    def __repr__(self) -> str:
        consolidate_repr = (
            f"\n  consolidate         : {self.consolidate}"
            if self.consolidate is not None
            else "\n  consolidate         : None"
        )
        return (
            f"EventsCleanerConfig(\n"
            f"  normalize_dates     : {self.normalize_dates}\n"
            f"  parse_dates         : {self.parse_dates}\n"
            f"  drop_duplicate_rows : {self.drop_duplicate_rows}"
            f"{consolidate_repr}\n"
            f"  date_floor          : {self.date_floor}\n"
            f"  date_ceiling        : {self.date_ceiling}\n"
            f")"
        )
