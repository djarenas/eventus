"""
bins_config.py

Standalone binning configuration, importable by any plot that needs it.
If a BinsConfig object exists, its spec is valid.

Supported bin types:
    auto      — delegate entirely to matplotlib
    uniform   — ~N equal-width bins between optional min/max
    log       — ~N bins on a log scale between optional min/max
    custom    — explicit bin edges [e0, e1, ..., eN] → N-1 bins
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias


# ── Spec variants ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AutoSpec:
    """Delegate bin calculation entirely to matplotlib."""
    type: Literal["auto"] = "auto"


@dataclass(frozen=True, slots=True)
class UniformSpec:
    """
    ~N equal-width bins.
    min and max are optional — when omitted they fall back to the data
    range at plot time. n_bins is a target; matplotlib may adjust
    slightly for clean boundaries.
    """
    type:   Literal["uniform"] = "uniform"
    n_bins: int                = 10
    min:    float | None       = None
    max:    float | None       = None

    def __post_init__(self) -> None:
        if self.n_bins <= 0:
            raise ValueError(f"bins.n_bins must be > 0, got {self.n_bins}")
        if self.min is not None and self.max is not None and self.min >= self.max:
            raise ValueError(
                f"bins.min ({self.min}) must be < bins.max ({self.max})"
            )


@dataclass(frozen=True, slots=True)
class LogSpec:
    """
    ~N bins on a log scale.
    min must be > 0 (log of zero is undefined).
    min and max are optional — fall back to data range at plot time.
    """
    type:   Literal["log"] = "log"
    n_bins: int             = 20
    min:    float | None    = None
    max:    float | None    = None

    def __post_init__(self) -> None:
        if self.n_bins <= 0:
            raise ValueError(f"bins.n_bins must be > 0, got {self.n_bins}")
        if self.min is not None and self.min <= 0:
            raise ValueError(
                f"bins.min must be > 0 for log bins, got {self.min}"
            )
        if self.max is not None and self.max <= 0:
            raise ValueError(
                f"bins.max must be > 0 for log bins, got {self.max}"
            )
        if self.min is not None and self.max is not None and self.min >= self.max:
            raise ValueError(
                f"bins.min ({self.min}) must be < bins.max ({self.max})"
            )


@dataclass(frozen=True, slots=True)
class CustomSpec:
    """
    Explicit bin edges. N edges produce N-1 bins.
    Edges must be strictly increasing and contain at least 2 values.
    Example: [0, 10, 25, 50, 100, 365]
    """
    type:  Literal["custom"] = "custom"
    edges: list[float]       = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.edges) < 2:
            raise ValueError(
                f"bins.edges must contain at least 2 values, got {len(self.edges)}"
            )
        if any(self.edges[i] >= self.edges[i + 1] for i in range(len(self.edges) - 1)):
            raise ValueError("bins.edges must be strictly increasing")


BinSpec: TypeAlias = AutoSpec | UniformSpec | LogSpec | CustomSpec

_SPEC_CLASSES: dict[str, type] = {
    "auto":    AutoSpec,
    "uniform": UniformSpec,
    "log":     LogSpec,
    "custom":  CustomSpec,
}


# ── Public class ──────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class BinsConfig:
    """
    Binning configuration. Composed into any plot config that needs binning.

    Use the friendly classmethods to construct:
        BinsConfig.auto()
        BinsConfig.uniform(n_bins=10, min=0, max=365)
        BinsConfig.log(n_bins=20, min=1, max=10_000)
        BinsConfig.custom(edges=[0, 10, 25, 50, 100, 365])

    Or load from a dict / YAML via BinsConfig.from_dict(data).
    """
    spec: BinSpec = field(default_factory=AutoSpec)

    def __post_init__(self) -> None:
        if not isinstance(self.spec, tuple(_SPEC_CLASSES.values())):
            raise TypeError(
                f"bins spec must be one of "
                f"{[c.__name__ for c in _SPEC_CLASSES.values()]}, "
                f"got {type(self.spec).__name__}"
            )

    @property
    def type(self) -> str:
        return self.spec.type

    # ── Friendly constructors ─────────────────────────────────────────────────

    @classmethod
    def auto(cls) -> "BinsConfig":
        """Delegate bin calculation to matplotlib."""
        return cls(AutoSpec())

    @classmethod
    def uniform(
        cls,
        *,
        n_bins: int = 10,
        min: float | None = None,
        max: float | None = None,
    ) -> "BinsConfig":
        """
        ~N equal-width bins between min and max.
        Omit min/max to use the data range at plot time.
        """
        return cls(UniformSpec(n_bins=n_bins, min=min, max=max))

    @classmethod
    def log(
        cls,
        *,
        n_bins: int = 20,
        min: float | None = None,
        max: float | None = None,
    ) -> "BinsConfig":
        """~N log-scale bins. min must be > 0 if provided."""
        return cls(LogSpec(n_bins=n_bins, min=min, max=max))

    @classmethod
    def custom(cls, *, edges: list[float]) -> "BinsConfig":
        """Explicit bin edges. N edges → N-1 bins. Must be strictly increasing."""
        return cls(CustomSpec(edges=edges))

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BinsConfig":
        """
        Build a BinsConfig from a plain dict (e.g. parsed from YAML).
        The 'type' key selects the spec; remaining keys are forwarded to it.
        Omitting 'type' defaults to 'auto'. Passing None returns BinsConfig.auto().

        Examples:
            BinsConfig.from_dict(None)
            BinsConfig.from_dict({"type": "uniform", "n_bins": 10, "min": 0, "max": 365})
            BinsConfig.from_dict({"type": "custom", "edges": [0, 10, 25, 50]})
        """
        if data is None:
            return cls.auto()

        if not isinstance(data, dict):
            raise TypeError(
                f"bins config must be a dict, got {type(data).__name__}"
            )

        bin_type = data.get("type", "auto")
        spec_cls = _SPEC_CLASSES.get(bin_type)
        if spec_cls is None:
            raise ValueError(
                f"bins.type must be one of {sorted(_SPEC_CLASSES)}, "
                f"got {bin_type!r}"
            )

        kwargs = {k: v for k, v in data.items() if k != "type"}
        return cls(spec_cls(**kwargs))

    def __repr__(self) -> str:
        return f"BinsConfig({self.spec})"
