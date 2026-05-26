"""
episodes_cleaner_config.py
Configuration dataclass for EpisodesCleaner.
Controls what counts as a valid row for a given dataset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import yaml

from eventus.cleaners.merge_config import MergeConfig

_ERROR_PREFIX = "[EpisodesCleanerConfig] Error"
_VALID_CAUSALITY = {"reject", "swap"}


@dataclass
class EpisodesCleanerConfig:
    """
    I am a reproducible set of rules for what counts as a valid episode
    row. I can be built from a YAML file and saved back to one.

    Parameters
    ----------
    normalize_dates : bool
        Strip time components from date columns — keep dates only.
        Default True.

    coalesce_dates : bool
        If a row is missing start OR end (but not both), fill the missing
        value from the other. If False (default), rows missing either
        date are rejected. Either way recorded in the quality report.

    causality_check : str
        What to do when end date is before start date.
        "reject" (default) — reject the row.
        "swap"             — swap start and end dates and keep the row.

    parse_dates : bool
        Auto-parse date columns from strings. Default True.

    drop_duplicates : bool
        Remove rows identical across entity_id, start, and end.
        Default True.

    merge : MergeConfig | None
        Merge overlapping or adjacent intervals after all other cleaning.
        None (default) — no merging.
        MergeConfig    — merge with the declared rules.

    date_floor : str
        Reject rows with start date before this date. Default "1920-01-01".

    date_ceiling : str
        Reject rows with end date after this date. Default "2100-01-01".

    Example YAML
    ------------
    normalize_dates: true
    coalesce_dates:  false
    causality_check: reject
    parse_dates:     true
    drop_duplicates: true
    date_floor:      "1920-01-01"
    date_ceiling:    "2100-01-01"

    merge:
      meaningful_gap_days: 1
      merge_mandates:
        - hospital_id
      descriptor_cols:
        icd10_condition:
          type: category
          aggregation_rule: unique
        bmi_at_admission:
          type: numeric
          aggregation_rule: median
    """

    normalize_dates:      bool               = True
    coalesce_dates:       bool               = False
    causality_check:      str                = "reject"
    parse_dates:          bool               = True
    drop_duplicate_rows:  bool               = True
    merge:                MergeConfig | None = None
    date_floor:           str                = "1920-01-01"
    date_ceiling:         str                = "2100-01-01"

    def __post_init__(self) -> None:
        if self.causality_check not in _VALID_CAUSALITY:
            raise ValueError(
                f"{_ERROR_PREFIX}: causality_check must be one of "
                f"{sorted(_VALID_CAUSALITY)}, got {self.causality_check!r}"
            )
        if self.merge is not None and not isinstance(self.merge, MergeConfig):
            raise ValueError(
                f"{_ERROR_PREFIX}: merge must be a MergeConfig or None, "
                f"got {type(self.merge).__name__}"
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
    def build_from_yaml(cls, path) -> "EpisodesCleanerConfig":
        """
        Build an EpisodesCleanerConfig from a YAML file.

        Parameters
        ----------
        path : str | pathlib.Path
            Path to the YAML config file.
        """
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)

        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML file must be a mapping, "
                f"got {type(cfg).__name__}"
            )

        known_keys = {
            "normalize_dates", "coalesce_dates", "causality_check",
            "parse_dates", "drop_duplicate_rows", "merge",
            "date_floor", "date_ceiling",
        }
        unknown = set(cfg.keys()) - known_keys
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown keys in YAML: {sorted(unknown)}. "
                f"Valid keys: {sorted(known_keys)}"
            )

        merge_data = cfg.pop("merge", None)
        merge      = MergeConfig.from_dict(merge_data) if merge_data else None

        return cls(**cfg, merge=merge)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def to_yaml(self, path) -> None:
        """Save this config to a YAML file."""
        cfg: dict[str, Any] = {
            "normalize_dates":     self.normalize_dates,
            "coalesce_dates":      self.coalesce_dates,
            "causality_check":     self.causality_check,
            "parse_dates":         self.parse_dates,
            "drop_duplicate_rows": self.drop_duplicate_rows,
            "date_floor":          self.date_floor,
            "date_ceiling":        self.date_ceiling,
        }
        if self.merge is not None:
            descriptor_cols = {
                col: {
                    "type":             dcfg.type,
                    "aggregation_rule": dcfg.aggregation_rule,
                }
                for col, dcfg in self.merge.descriptor_cols.items()
            }
            cfg["merge"] = {
                "meaningful_gap_days": self.merge.meaningful_gap_days,
                "descriptor_cols":     descriptor_cols,
            }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)

    def __repr__(self) -> str:
        merge_repr = (
            f"\n  merge               : {self.merge}"
            if self.merge is not None
            else "\n  merge               : None"
        )
        return (
            f"EpisodesCleanerConfig(\n"
            f"  normalize_dates     : {self.normalize_dates}\n"
            f"  coalesce_dates      : {self.coalesce_dates}\n"
            f"  causality_check     : '{self.causality_check}'\n"
            f"  parse_dates         : {self.parse_dates}\n"
            f"  drop_duplicate_rows : {self.drop_duplicate_rows}"
            f"{merge_repr}\n"
            f"  date_floor          : {self.date_floor}\n"
            f"  date_ceiling        : {self.date_ceiling}\n"
            f")"
        )
