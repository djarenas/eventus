"""
events_cleaner_config.py
Configuration dataclass for EventsCleaner.
Controls what counts as a valid row for a given dataset.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
import yaml

_ERROR_PREFIX = "[EventsCleanerConfig] Error"

_VALID_CAUSALITY = {"reject", "swap"}


@dataclass
class EventsCleanerConfig:
    """
    'I am a reproducible set of rules for what counts as a valid event row. I can be built from a YAML file and saved back to one'

    All parameters have sensible defaults suitable for most clinical and
    insurance datasets. Override via build_from_yaml() to make your
    cleaning choices explicit, versioned, and reproducible.

    Parameters
    ----------
    normalize_dates : bool
        Strip time components from date columns — keep dates only.
        Default True. Recommended for clinical data where time of day
        is unreliable or irrelevant.

    coalesce_dates : bool
        If a row is missing start OR end (but not both), fill the missing
        value from the other. If False (default), rows missing either
        date are rejected. Either way the action is recorded in the
        quality report.

    causality_check : str
        What to do when end date is before start date.
        "reject" (default) — reject the row.
        "swap"             — swap start and end dates and keep the row.
        Either way the action is recorded in the quality report.

    parse_dates : bool
        Auto-parse date columns from strings. Default True.

    drop_duplicates : bool
        Remove rows that are identical across entity_id, start, and end.
        Default True.

    merge_overlapping : bool
        Merge overlapping or adjacent intervals after all other cleaning.
        Default False.

    meaningful_gap : int
        Days between intervals below which they are merged into one episode.
        Only used when merge_overlapping=True. Default 0.

    date_floor : str
        Reject rows with start date before this date. Default "1920-01-01".

    date_ceiling : str
        Reject rows with end date after this date. Default "2100-01-01".
    """

    normalize_dates:  bool = True
    coalesce_dates:   bool = False
    causality_check:  str  = "reject"
    parse_dates:      bool = True
    drop_duplicates:  bool = True
    merge_overlapping: bool = False
    meaningful_gap:   int  = 0
    date_floor:       str  = "1920-01-01"
    date_ceiling:     str  = "2100-01-01"

    def __post_init__(self) -> None:
        # Validate causality_check
        if self.causality_check not in _VALID_CAUSALITY:
            raise ValueError(
                f"{_ERROR_PREFIX}: causality_check must be one of "
                f"{sorted(_VALID_CAUSALITY)}, got {self.causality_check!r}"
            )
        # Validate meaningful_gap
        if not isinstance(self.meaningful_gap, int) or self.meaningful_gap < 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: meaningful_gap must be a non-negative integer, "
                f"got {self.meaningful_gap!r}"
            )
        # Validate date_floor and date_ceiling
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
    def build_from_yaml(cls, path: str) -> "EventsCleanerConfig":
        """
        Build an EventsCleanerConfig from a YAML file.

        Parameters
        ----------
        path : str
            Path to the YAML config file.

        Returns
        -------
        EventsCleanerConfig
            Validated config object.

        Example YAML
        ------------
        normalize_dates:   true
        coalesce_dates:    false
        causality_check:   reject
        parse_dates:       true
        drop_duplicates:   true
        merge_overlapping: false
        meaningful_gap:    0
        date_floor:        "1920-01-01"
        date_ceiling:      "2100-01-01"
        """
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)

        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML file must be a mapping, "
                f"got {type(cfg).__name__}"
            )

        valid_keys = set(cls.__dataclass_fields__.keys())
        unknown    = set(cfg.keys()) - valid_keys
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unknown keys in YAML: {sorted(unknown)}. "
                f"Valid keys: {sorted(valid_keys)}"
            )

        return cls(**cfg)

    @classmethod
    def build_with_defaults(cls) -> "EventsCleanerConfig":
        """
        A minimal config — only the safest, most essential cleaning.
        No date floor/ceiling checks, no merging, no coalescing.
        Good for data you mostly trust but want null/duplicate handling.
        """
        return cls(
            normalize_dates  = True,
            coalesce_dates   = False,
            causality_check  = "reject",
            parse_dates      = True,
            drop_duplicates  = True,
            merge_overlapping = False,
            meaningful_gap   = 0,
            date_floor       = "1800-01-01",
            date_ceiling      = "2200-01-01",
        )

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {
            "normalize_dates":  self.normalize_dates,
            "coalesce_dates":   self.coalesce_dates,
            "causality_check":  self.causality_check,
            "parse_dates":      self.parse_dates,
            "drop_duplicates":  self.drop_duplicates,
            "merge_overlapping": self.merge_overlapping,
            "meaningful_gap":   self.meaningful_gap,
            "date_floor":       self.date_floor,
            "date_ceiling":     self.date_ceiling,
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        return (
            f"EventsCleanerConfig(\n"
            f"  normalize_dates  : {self.normalize_dates}\n"
            f"  coalesce_dates   : {self.coalesce_dates}\n"
            f"  causality_check  : '{self.causality_check}'\n"
            f"  parse_dates      : {self.parse_dates}\n"
            f"  drop_duplicates  : {self.drop_duplicates}\n"
            f"  merge_overlapping: {self.merge_overlapping}\n"
            f"  meaningful_gap   : {self.meaningful_gap} days\n"
            f"  date_floor       : {self.date_floor}\n"
            f"  date_ceiling     : {self.date_ceiling}\n"
            f")"
        )
