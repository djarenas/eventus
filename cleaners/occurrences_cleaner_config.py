"""
occurrences_cleaner_config.py
Configuration dataclass for OccurrencesCleaner.
Controls what counts as a valid row for a given occurrences dataset.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
import yaml

_ERROR_PREFIX = "[OccurrencesCleanerConfig] Error"


@dataclass
class OccurrencesCleanerConfig:
    """
    Configuration for OccurrencesCleaner — controls how raw occurrence
    data is cleaned.

    All parameters have sensible defaults suitable for most clinical
    datasets. Override via build_from_yaml() to make your cleaning
    choices explicit, versioned, and reproducible.

    Parameters
    ----------
    normalize_dates : bool
        Strip time components — keep dates only. Default True.

    parse_dates : bool
        Auto-parse date column from strings. Default True.

    drop_duplicates : bool
        Remove rows identical across entity_id and date. Default True.

    date_floor : str
        Reject rows with date before this value. Default "1920-01-01".

    date_ceiling : str
        Reject rows with date after this value. Default "2100-01-01".
    """

    normalize_dates: bool = True
    parse_dates:     bool = True
    drop_duplicates: bool = True
    date_floor:      str  = "1920-01-01"
    date_ceiling:    str  = "2100-01-01"

    def __post_init__(self) -> None:
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
    def build_from_yaml(cls, path: str) -> "OccurrencesCleanerConfig":
        """
        Build an OccurrencesCleanerConfig from a YAML file.

        Example YAML
        ------------
        normalize_dates: true
        parse_dates:     true
        drop_duplicates: true
        date_floor:      "1920-01-01"
        date_ceiling:    "2100-01-01"
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
    def build_with_defaults(cls) -> "OccurrencesCleanerConfig":
        """
        A minimal config — only the safest, most essential cleaning.
        No date floor/ceiling checks.
        Good for data you mostly trust but want null/duplicate handling.
        """
        return cls(
            normalize_dates = True,
            parse_dates     = True,
            drop_duplicates = True,
            date_floor      = "1800-01-01",
            date_ceiling    = "2200-01-01",
        )

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {
            "normalize_dates": self.normalize_dates,
            "parse_dates":     self.parse_dates,
            "drop_duplicates": self.drop_duplicates,
            "date_floor":      self.date_floor,
            "date_ceiling":    self.date_ceiling,
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        return (
            f"OccurrencesCleanerConfig(\n"
            f"  normalize_dates : {self.normalize_dates}\n"
            f"  parse_dates     : {self.parse_dates}\n"
            f"  drop_duplicates : {self.drop_duplicates}\n"
            f"  date_floor      : {self.date_floor}\n"
            f"  date_ceiling    : {self.date_ceiling}\n"
            f")"
        )
