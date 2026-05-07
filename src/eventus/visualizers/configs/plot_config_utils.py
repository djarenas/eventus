"""
general_plot_config_utils.py
Shared validation helpers for eventus plot config modules.
"""
from __future__ import annotations    
import dataclasses  
import yaml
import math  
from pathlib import Path  
from typing import Any, Mapping  
from collections.abc import Sequence
  
  
_DEFAULT_PALETTE = [  
    "#028090", "#E05C40", "#6B4FA0", "#E09820", "#2C7BB6",  
    "#D7191C", "#1A9641", "#FDAE61", "#ABD9E9", "#F46D43",  
]  
  
  
def err(prefix: str, msg: str) -> ValueError:  
    return ValueError(f"[{prefix}] Error: {msg}")  
  
  
# ── YAML / structure helpers ──────────────────────────────────────────────────  
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
    """Validate top-level section keys."""  
    unknown = set(data.keys()) - valid_sections  
    if unknown:  
        raise err(  
            prefix,  
            f"unknown {context}: {sorted(unknown)}. Valid: {sorted(valid_sections)}",  
        )  

def validate_font_size(value: int | str | None, prefix: str) -> int | None:  
    if value is None:  
        return None  
    if isinstance(value, bool):  
        raise err(prefix, "font_size must be an int or None, got bool")  
    try:  
        value = int(value)  
    except (TypeError, ValueError) as e:  
        raise err(prefix, f"Could not convert font_size={value!r} to int") from e  
    if not (1 <= value <= 99):  
        raise err(prefix, f"font_size must be between 1 and 99, got {value}")  
    return value  

def validate_ticks(value_list: Sequence[float | int | str] | None, prefix) -> list[float] | None:  
    if value_list is None:  
        return None  
    if isinstance(value_list, (str, bytes)) or not isinstance(value_list, Sequence):  
        raise ValueError(f"{prefix}: ticks must be a sequence of numbers, got {type(value_list).__name__}")  
    out: list[float] = []  
    for i, x in enumerate(value_list):  
        if isinstance(x, bool):  
            raise ValueError(f"{prefix}: ticks[{i}] must be numeric, got bool")  
        try:  
            out.append(float(x))  
        except (TypeError, ValueError) as e:  
            raise ValueError(f"{prefix}: Could not convert ticks[{i}]={x!r} to float") from e  
    return out  

def validate_rotation(value: float | int | str, prefix) -> float:  
    return validate_float_in_range(  
        value,  
        min_value=0.0,  
        max_value=360.0, 
        prefix = prefix,
        name="rotation",  
        inclusive=True,  
        finite_only=True,  
    )  

# ── Field validators ──────────────────────────────────────────────────────────  
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
  
  
def validate_choice(value: str, valid: set[str], prefix: str, field_name: str) -> None:  
    if value not in valid:  
        raise err(prefix, f"{field_name} must be one of {sorted(valid)}, got {value!r}")  
  
  
def validate_alpha(value: float, prefix: str, field_name: str = 'alpha') -> float:  
    value = validate_positive_float(value, prefix, field_name)
    if not (0.0 <= value <= 1.0):  
        raise err(prefix, f"Invalid {field_name} value. Value must be between 0 and 1.")  
    return value
  
def validate_figsize(figsize: Any, prefix: str) -> tuple[float, float]:  
    """Validate and coerce figsize to a (width, height) tuple."""  
    try:
        fs = tuple(figsize)  
    except Exception as e:
        raise err(prefix, f"figsize must be a tuple or at least convertible to a tuple: {e}")    
    if len(fs) != 2 or not all(v > 0 for v in fs):  
        raise err(prefix, f"figsize must be [width, height] with both values > 0, got {list(figsize)}")  
    return fs  # type: ignore[return-value]  
  
  
def build_section(cls_, data: dict | None, prefix: str):  
    """Instantiate a dataclass from a dict, raising on unknown keys."""  
    if data is None:  
        return cls_()  
    valid = set(cls_.__dataclass_fields__.keys())  
    unknown = set(data.keys()) - valid  
    if unknown:  
        raise err(prefix, f"unknown keys in '{cls_.__name__}': {sorted(unknown)}")  
    return cls_(**data)  


  
# ── Format validators ──────────────────────────────────────────────────────────  
  
def validate_integer(value: str | int, prefix: str, name: str = "value") -> int:  
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
  
  
def validate_float(  value: str | int | float, prefix, name: str = "value", finite_only: bool = True) -> float:  
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
  

# ── Built on the two base validators ───────────────────────────────────────  
  
def validate_positive_integer(value: str | int, prefix: str, name: str = "value") -> int:  
    out = validate_integer(value, prefix, name)  
    if out < 0:  
        raise err(prefix, f"{name} must be >= 0, got {out}")  
    return out  
  
  
def validate_positive_float(  
    value: str | int | float,
    prefix: str,  
    name: str = "value",  
    *,  
    finite_only: bool = True,  
) -> float:  
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
    if min_value > max_value:  
        raise ValueError(f"Error in validate_float_in_range(): min_value ({min_value}) cannot exceed max_value ({max_value})")  
  
    out = validate_float(value, name, finite_only=finite_only)  
  
    if inclusive:  
        ok = (min_value <= out <= max_value)  
        rng = f"[{min_value}, {max_value}]"  
    else:  
        ok = (min_value < out < max_value)  
        rng = f"({min_value}, {max_value})"  
  
    if not ok:  
        raise err(prefix, f"{name} must be in {rng}, got {out}")  
  
    return out  