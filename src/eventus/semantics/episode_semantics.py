"""
episode_semantics.py
EpisodeSemantics — maps generic concepts to specific column names
in episode (interval) data.
"""
from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from typing import Any

from eventus.semantics.descriptor_col_config import DescriptorColConfig

_ERROR_PREFIX = "[EpisodeSemantics] Error"

REQUIRED_FIELDS = {"entity_id_col", "start_time_col", "end_time_col"}
OPTIONAL_FIELDS = {
    "identity", "also_defined_by", "descriptor_cols",
    "episode_id_col", "episode_type_col",
}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass
class EpisodeSemantics:
    """
    I am a description of what columns mean in episode data.
    I hold no data and do no computation.

    Maps generic concepts to specific column names in a DataFrame.
    Decouple all downstream logic from specific data schemas — define
    once, reuse everywhere.

    Parameters
    ----------
    identity : str | None
        What kind of episodes these are. Letters, numbers, and underscores
        only. Flows into intermediate column names and plot titles.
        e.g. 'inpatient_hospitalization', 'medicaid_coverage'.

    entity_id_col : str
        Column identifying the entity (patient, member, etc.).

    start_time_col : str
        Column for episode start date.

    end_time_col : str
        Column for episode end date.

    also_defined_by : list[str] | None
        Columns that are part of the episode's identity — two intervals
        can only be merged if all also_defined_by columns match.
        e.g. ["hospital_id"] means a hospitalization IS defined by
        its hospital — stays at different hospitals are never merged
        even if they overlap in time.

    descriptor_cols : dict[str, DescriptorColConfig] | None
        Columns that describe the episode but are not part of its
        identity. Aggregated during merging according to rules
        declared in EpisodesCleanerConfig.merge.
        e.g. {"icd10_condition": DescriptorColConfig(type="category")}

    episode_id_col : str | None
        Optional column for a unique episode identifier.

    episode_type_col : str | None
        Optional column for episode type or category.

    Examples
    --------
    >>> sem = EpisodeSemantics(
    ...     identity        = "inpatient_hospitalization",
    ...     entity_id_col   = "patient_id",
    ...     start_time_col  = "admit_date",
    ...     end_time_col    = "discharge_date",
    ...     also_defined_by = ["hospital_id"],
    ...     descriptor_cols = {
    ...         "icd10_condition": DescriptorColConfig(type="category"),
    ...         "bmi_at_admission": DescriptorColConfig(type="numeric"),
    ...     },
    ... )
    """

    identity:        str | None                          = None
    entity_id_col:   str                                 = ""
    start_time_col:  str                                 = ""
    end_time_col:    str                                 = ""
    also_defined_by: list[str] | None                    = None
    descriptor_cols: dict[str, DescriptorColConfig] | None = None
    episode_id_col:    str | None                          = None
    episode_type_col:  str | None                          = None

    def __post_init__(self) -> None:
        # Validate required string fields
        for attr in ("entity_id_col", "start_time_col", "end_time_col"):
            val = getattr(self, attr)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(
                    f"{_ERROR_PREFIX}: '{attr}' must be a non-empty string, "
                    f"got {val!r}"
                )

        # Validate identity
        if self.identity is not None:
            if not re.match(r'^[a-zA-Z0-9_]+$', self.identity):
                raise ValueError(
                    f"{_ERROR_PREFIX}: identity {self.identity!r} contains "
                    f"invalid characters. Use only letters, numbers, and "
                    f"underscores e.g. 'inpatient_hospitalization'"
                )

        # Validate also_defined_by
        if self.also_defined_by is not None:
            if not isinstance(self.also_defined_by, list):
                raise ValueError(
                    f"{_ERROR_PREFIX}: also_defined_by must be a list, "
                    f"got {type(self.also_defined_by).__name__}"
                )

        # Validate descriptor_cols
        if self.descriptor_cols is not None:
            if not isinstance(self.descriptor_cols, dict):
                raise ValueError(
                    f"{_ERROR_PREFIX}: descriptor_cols must be a dict, "
                    f"got {type(self.descriptor_cols).__name__}"
                )
            for col, cfg in self.descriptor_cols.items():
                if not isinstance(cfg, DescriptorColConfig):
                    raise ValueError(
                        f"{_ERROR_PREFIX}: descriptor_cols[{col!r}] must be "
                        f"a DescriptorColConfig, got {type(cfg).__name__}"
                    )

        # also_defined_by and descriptor_cols must be disjoint
        if self.also_defined_by and self.descriptor_cols:
            overlap = set(self.also_defined_by) & set(self.descriptor_cols)
            if overlap:
                raise ValueError(
                    f"{_ERROR_PREFIX}: columns cannot appear in both "
                    f"also_defined_by and descriptor_cols: {sorted(overlap)}"
                )

    # ── Convenience properties ────────────────────────────────────────────

    @property
    def metadata_cols(self) -> list[str]:
        """
        All metadata column names — also_defined_by + descriptor_cols keys.
        Convenience property for downstream code that needs all extra columns.
        """
        cols = list(self.also_defined_by or [])
        cols += list(self.descriptor_cols.keys() if self.descriptor_cols else [])
        return cols

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def build_from_yaml(cls, path) -> "EpisodeSemantics":
        """
        Build an EpisodeSemantics from a YAML file.

        Example YAML
        ------------
        identity:        inpatient_hospitalization
        entity_id_col:   patient_id
        start_time_col:  admit_date
        end_time_col:    discharge_date
        also_defined_by:
          - hospital_id
        descriptor_cols:
          icd10_condition:
            type: category
          bmi_at_admission:
            type: numeric
        """
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)

        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML at '{path}' must be a mapping, "
                f"got {type(cfg).__name__}"
            )

        missing = REQUIRED_FIELDS - set(cfg.keys())
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: missing required fields in '{path}': "
                f"{sorted(missing)}"
            )

        unknown = set(cfg.keys()) - ALL_FIELDS
        if unknown:
            raise ValueError(
                f"{_ERROR_PREFIX}: unrecognized fields in '{path}': "
                f"{sorted(unknown)}"
            )

        # Parse descriptor_cols
        descriptor_cols = None
        if "descriptor_cols" in cfg and cfg["descriptor_cols"]:
            descriptor_cols = {
                col: DescriptorColConfig.from_dict(dcfg)
                for col, dcfg in cfg["descriptor_cols"].items()
            }
            cfg["descriptor_cols"] = descriptor_cols

        return cls(**cfg)

    def to_yaml(self, path) -> None:
        """Save this semantics to a YAML file."""
        out: dict[str, Any] = {
            "identity":       self.identity,
            "entity_id_col":  self.entity_id_col,
            "start_time_col": self.start_time_col,
            "end_time_col":   self.end_time_col,
        }
        if self.also_defined_by:
            out["also_defined_by"] = self.also_defined_by
        if self.descriptor_cols:
            out["descriptor_cols"] = {
                col: {"type": cfg.type}
                for col, cfg in self.descriptor_cols.items()
            }
        if self.episode_id_col:
            out["episode_id_col"] = self.episode_id_col
        if self.episode_type_col:
            out["episode_type_col"] = self.episode_type_col

        with open(path, "w") as f:
            yaml.dump(out, f, sort_keys=False, default_flow_style=False)

    def __repr__(self) -> str:
        also = self.also_defined_by or []
        desc = list(self.descriptor_cols.keys()) if self.descriptor_cols else []
        return (
            f"EpisodeSemantics(\n"
            f"  identity        : {self.identity!r}\n"
            f"  entity_id_col   : '{self.entity_id_col}'\n"
            f"  start_time_col  : '{self.start_time_col}'\n"
            f"  end_time_col    : '{self.end_time_col}'\n"
            f"  also_defined_by : {also}\n"
            f"  descriptor_cols : {desc}\n"
            f")"
        )
