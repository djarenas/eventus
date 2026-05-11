"""
plot_config_utils.py
Shared validation helpers for eventus plot config modules.

Organisation
------------
1. Constants
2. Error helper
3. YAML / structure helpers
4. Base type validators          (integer, float)
5. Derived numeric validators    (positive_integer, positive_float, float_in_range)
6. Specific field validators     (alpha, hex, choice, figsize, rotation, ticks, font_size)
7. Section builder
"""
from __future__ import annotations

import dataclasses
import math
import yaml
from pathlib import Path
from typing import Any, Mapping
from collections.abc import Sequence


# ── 1. Constants ──────────────────────────────────────────────────────────────

_DEFAULT_PALETTE = [
    "#028090", "#E05C40", "#6B4FA0", "#E09820", "#2C7BB6",
    "#D7191C", "#1A9641", "#FDAE61", "#ABD9E9", "#F46D43",
]


# ── 2. Error helper ───────────────────────────────────────────────────────────

def err(prefix: str, msg: str) -> ValueError:
    return ValueError(f"[{prefix}] {msg}")


# ── 3. YAML / structure helpers ───────────────────────────────────────────────

def load_yaml_mapping(path: str | Path, prefix: str) -> dict[str, Any]:
    """Load YAML and require a top-level mapping."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise err(prefix, f"YAML must be a mapping, got {type(raw).__name__}")
    return raw


def dump_yaml_dataclass(obj: Any, path: str | Path) -> None:
    """Dump a dataclass (or dict-like structure) to YAML."""
    def _coerce(x: Any) -> Any:
        if dataclasses.is_dataclass(x):
            return _coerce(dataclasses.asdict(x))
        if isinstance(x, dict):
            return {k: _coerce(v) for k, v in x.items()}
        if isinstance(x, (tuple, list)):
            return [_coerce(v) for v in x]
        return x

    with open(path, "w") as f:
        yaml.dump(_coerce(obj), f, sort_keys=False, default_flow_style=False)


def validate_sections(
    data: Mapping[str, Any],
    valid_sections: set[str],
    prefix: str,
    context: str = "sections",
) -> None:
    """Raise if data contains any key not in valid_sections."""
    unknown = set(data.keys()) - valid_sections
    if unknown:
        raise err(
            prefix,
            f"unknown {context}: {sorted(unknown)}. Valid: {sorted(valid_sections)}",
        )


# ── 4. Base type validators ───────────────────────────────────────────────────

def validate_integer(value: str | int, prefix: str, name: str = "value") -> int:
    """Coerce value to int. Rejects bools, floats, and non-integer strings."""
    if isinstance(value, bool):
        raise err(prefix, f"{name} must be an integer, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise err(prefix, f"{name} cannot be empty")
        if s[0] in "+-":
            digits = s[1:]
            if not digits.isdigit():
                raise err(prefix, f"{name} must be an integer string, got {value!r}")
        elif not s.isdigit():
            raise err(prefix, f"{name} must be an integer string, got {value!r}")
        return int(s)
    raise err(prefix, f"{name} must be int or integer-like str, got {type(value).__name__}")


def validate_float(
    value: str | int | float,
    prefix: str,
    name: str = "value",
    *,
    finite_only: bool = True,
) -> float:
    """Coerce value to float. Rejects bools. Optionally rejects non-finite values."""
    if isinstance(value, bool):
        raise err(prefix, f"{name} must be a float, got bool")
    if not isinstance(value, (int, float, str)):
        raise err(prefix, f"{name} must be int, float, or float-like str, got {type(value).__name__}")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise err(prefix, f"{name} could not be converted to float: {value!r}")
    if finite_only and not math.isfinite(out):
        raise err(prefix, f"{name} must be finite, got {out!r}")
    return out


# ── 5. Derived numeric validators ─────────────────────────────────────────────

def validate_non_negative_integer(value: str | int, prefix: str, name: str = "value") -> int:
    """Validate that value is an integer >= 0."""
    out = validate_integer(value, prefix, name)
    if out < 0:
        raise err(prefix, f"{name} must be >= 0, got {out}")
    return out


def validate_positive_integer(value: str | int, prefix: str, name: str = "value") -> int:
    """Validate that value is an integer > 0."""
    out = validate_integer(value, prefix, name)
    if out <= 0:
        raise err(prefix, f"{name} must be > 0, got {out}")
    return out


def validate_positive_float(
    value: str | int | float,
    prefix: str,
    name: str = "value",
    *,
    finite_only: bool = True,
) -> float:
    """Validate that value is a float >= 0."""
    out = validate_float(value, prefix, name, finite_only=finite_only)
    if out < 0.0:
        raise err(prefix, f"{name} must be >= 0, got {out}")
    return out


def validate_float_in_range(
    value: str | int | float,
    min_value: float,
    max_value: float,
    prefix: str,
    name: str = "value",
    *,
    inclusive: bool = True,
    finite_only: bool = True,
) -> float:
    """Validate that value is a float within [min_value, max_value] (or exclusive)."""
    if min_value > max_value:
        raise ValueError(
            f"validate_float_in_range: min_value ({min_value}) cannot exceed max_value ({max_value})"
        )
    out = validate_float(value, prefix, name, finite_only=finite_only)
    if inclusive:
        ok = min_value <= out <= max_value
        rng = f"[{min_value}, {max_value}]"
    else:
        ok = min_value < out < max_value
        rng = f"({min_value}, {max_value})"
    if not ok:
        raise err(prefix, f"{name} must be in {rng}, got {out}")
    return out


# ── 6. Specific field validators ──────────────────────────────────────────────

def validate_alpha(value: float, prefix: str, field_name: str = "alpha") -> float:
    """Validate that value is a float in [0.0, 1.0]."""
    return validate_float_in_range(
        value,
        min_value=0.0,
        max_value=1.0,
        prefix=prefix,
        name=field_name,
        inclusive=True,
    )


def validate_hex(value: str, field_name: str, prefix: str) -> None:
    """Accept 6-digit (#RRGGBB) or 3-digit (#RGB) hex color strings."""
    if not (
        isinstance(value, str)
        and value.startswith("#")
        and len(value) in (4, 7)
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    ):
        raise err(
            prefix,
            f"{field_name} must be a hex color like '#028090' or '#FFF', got {value!r}",
        )


def validate_choice(value: str, valid: set[str], field_name: str, prefix: str) -> None:
    """Validate that value is one of the allowed choices."""
    if value not in valid:
        raise err(prefix, f"{field_name} must be one of {sorted(valid)}, got {value!r}")


def validate_figsize(figsize: Any, prefix: str) -> tuple[float, float]:
    """Validate and coerce figsize to a (width, height) tuple of positive floats."""
    try:
        fs = tuple(figsize)
    except Exception as e:
        raise err(prefix, f"figsize must be a sequence of two positive numbers: {e}")
    if len(fs) != 2 or not all(v > 0 for v in fs):
        raise err(prefix, f"figsize must be [width, height] with both values > 0, got {list(figsize)}")
    return fs  # type: ignore[return-value]


def validate_rotation(value: float | int | str, prefix: str, name: str = "rotation") -> float:
    """Validate that value is a float in [0.0, 360.0]."""
    return validate_float_in_range(
        value,
        min_value=0.0,
        max_value=360.0,
        prefix=prefix,
        name=name,
        inclusive=True,
        finite_only=True,
    )


def validate_ticks(
    value_list: Sequence[float | int | str] | None,
    prefix: str,
    name: str = "ticks",
) -> list[float] | None:
    """Validate and coerce a sequence of tick values to list[float], or None."""
    if value_list is None:
        return None
    if isinstance(value_list, (str, bytes)) or not isinstance(value_list, Sequence):
        raise err(prefix, f"{name} must be a sequence of numbers, got {type(value_list).__name__}")
    out: list[float] = []
    for i, x in enumerate(value_list):
        if isinstance(x, bool):
            raise err(prefix, f"{name}[{i}] must be numeric, got bool")
        try:
            out.append(float(x))
        except (TypeError, ValueError) as e:
            raise err(prefix, f"could not convert {name}[{i}]={x!r} to float") from e
    return out


def validate_font_size(value: int | str | None, prefix: str, name: str = "font_size") -> int | None:
    """Validate that value is an integer in [1, 99], or None."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise err(prefix, f"{name} must be an int or None, got bool")
    try:
        value = int(value)
    except (TypeError, ValueError) as e:
        raise err(prefix, f"could not convert {name}={value!r} to int") from e
    if not (1 <= value <= 99):
        raise err(prefix, f"{name} must be between 1 and 99, got {value}")
    return value


# ── 7. Section builder ────────────────────────────────────────────────────────

def build_section(cls_, data: dict | None, prefix: str):
    """Instantiate a config dataclass from a dict, raising on unknown keys."""
    if data is None:
        return cls_()
    valid = set(cls_.__dataclass_fields__.keys())
    unknown = set(data.keys()) - valid
    if unknown:
        raise err(prefix, f"unknown keys in '{cls_.__name__}': {sorted(unknown)}")
    return cls_(**data)
