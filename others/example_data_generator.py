"""
generate_example_events_data.py
ExampleDataConfig and ExampleDataGenerator — synthetic event and demographics
data for eventus vignettes and testing.

Edit ExampleDataConfig or build from YAML to control generation and noise.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import yaml

_ERROR_PREFIX  = "[ExampleDataConfig] Error"
_VALID_LEVELS  = {"row", "patient"}


# ══════════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class ExampleDataConfig:
    """
    Configuration for ExampleDataGenerator.

    Controls both the generation of clean synthetic event data and
    the injection of realistic noise for cleaning vignettes.

    Generation settings
    -------------------
    n_patients : int
        Number of unique entities. Default 50.
    obs_period_start : str
        Start of the observation period (ISO format). Default "2022-01-01".
    obs_period_end : str
        End of the observation period (ISO format). Default "2022-06-30".
    min_events : int
        Minimum events per entity. 0 means some entities have no events
        and will not appear in the output — realistic for claims data.
        Default 0.
    max_events : int
        Maximum events per entity. Default 10.
    min_event_days : int
        Minimum event duration in days. Default 1.
    max_event_days : int
        Maximum event duration in days. Default 30.
    dob_year_min : int
        Earliest birth year for demographics. Default 2000.
    dob_year_max : int
        Latest birth year for demographics. Default 2005.
    random_seed : int
        Random seed for reproducibility. Default 42.

    Noise injection settings
    ------------------------
    Each noise parameter is a fraction (0.0–1.0) and has a companion
    _level parameter ("row" or "patient"):

    - "row"     : fraction of total generated rows are affected
    - "patient" : fraction of unique patients each get one affected row

    frac_overlapping_pairs is always patient-level — it injects a pair
    of overlapping rows per affected patient, so no _level companion.

    Parameters default to small realistic fractions matching typical
    claims data quality issues.
    """

    # ── Generation ────────────────────────────────────────────────────────
    n_patients:       int = 50
    obs_period_start: str = "2022-01-01"
    obs_period_end:   str = "2022-06-30"
    min_events:       int = 0
    max_events:       int = 10
    min_event_days:   int = 1
    max_event_days:   int = 30
    dob_year_min:     int = 2000
    dob_year_max:     int = 2005
    random_seed:      int = 42

    # ── Noise fractions ───────────────────────────────────────────────────
    frac_null_entity_ids:       float = 0.01
    frac_null_start_dates:      float = 0.03
    frac_null_end_dates:        float = 0.03
    frac_unparseable_dates:     float = 0.01
    frac_before_floor:          float = 0.01
    frac_after_ceiling:         float = 0.01
    frac_causality_violations:  float = 0.02
    frac_duplicates:            float = 0.05
    frac_timestamps:            float = 0.02
    frac_overlapping_pairs:     float = 0.02

    # ── Noise levels ──────────────────────────────────────────────────────
    null_entity_ids_level:      str = "row"
    null_start_dates_level:     str = "row"
    null_end_dates_level:       str = "row"
    unparseable_dates_level:    str = "row"
    before_floor_level:         str = "row"
    after_ceiling_level:        str = "row"
    causality_violations_level: str = "row"
    duplicates_level:           str = "row"
    timestamps_level:           str = "row"

    def __post_init__(self) -> None:
        # ── Generation validation ─────────────────────────────────────────
        if self.n_patients < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: n_patients must be >= 1, "
                f"got {self.n_patients}"
            )
        try:
            obs_start = pd.Timestamp(self.obs_period_start)
            obs_end   = pd.Timestamp(self.obs_period_end)
        except Exception as e:
            raise ValueError(
                f"{_ERROR_PREFIX}: invalid obs_period_start or "
                f"obs_period_end: {e}"
            )
        if obs_start >= obs_end:
            raise ValueError(
                f"{_ERROR_PREFIX}: obs_period_start ({self.obs_period_start}) "
                f"must be before obs_period_end ({self.obs_period_end})"
            )
        if self.min_events < 0:
            raise ValueError(
                f"{_ERROR_PREFIX}: min_events must be >= 0, "
                f"got {self.min_events}"
            )
        if self.min_events > self.max_events:
            raise ValueError(
                f"{_ERROR_PREFIX}: min_events ({self.min_events}) must be "
                f"<= max_events ({self.max_events})"
            )
        if self.min_event_days < 1:
            raise ValueError(
                f"{_ERROR_PREFIX}: min_event_days must be >= 1, "
                f"got {self.min_event_days}"
            )
        if self.min_event_days > self.max_event_days:
            raise ValueError(
                f"{_ERROR_PREFIX}: min_event_days ({self.min_event_days}) "
                f"must be <= max_event_days ({self.max_event_days})"
            )
        if self.dob_year_min > self.dob_year_max:
            raise ValueError(
                f"{_ERROR_PREFIX}: dob_year_min ({self.dob_year_min}) must be "
                f"<= dob_year_max ({self.dob_year_max})"
            )

        # ── Noise fraction validation ─────────────────────────────────────
        frac_fields = [
            "frac_null_entity_ids",
            "frac_null_start_dates",
            "frac_null_end_dates",
            "frac_unparseable_dates",
            "frac_before_floor",
            "frac_after_ceiling",
            "frac_causality_violations",
            "frac_duplicates",
            "frac_timestamps",
            "frac_overlapping_pairs",
        ]
        for fname in frac_fields:
            val = getattr(self, fname)
            if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"{_ERROR_PREFIX}: {fname} must be a float between "
                    f"0.0 and 1.0, got {val!r}"
                )

        # ── Noise level validation ────────────────────────────────────────
        level_fields = [
            "null_entity_ids_level",
            "null_start_dates_level",
            "null_end_dates_level",
            "unparseable_dates_level",
            "before_floor_level",
            "after_ceiling_level",
            "causality_violations_level",
            "duplicates_level",
            "timestamps_level",
        ]
        for lname in level_fields:
            val = getattr(self, lname)
            if val not in _VALID_LEVELS:
                raise ValueError(
                    f"{_ERROR_PREFIX}: {lname} must be one of "
                    f"{sorted(_VALID_LEVELS)}, got {val!r}"
                )

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_from_yaml(cls, path: str) -> "ExampleDataConfig":
        """Build an ExampleDataConfig from a YAML file."""
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must be a mapping, "
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
    def build_with_defaults(cls) -> "ExampleDataConfig":
        """Return an ExampleDataConfig with all defaults."""
        return cls()

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        cfg = {k: getattr(self, k) for k in self.__dataclass_fields__}
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    def __repr__(self) -> str:
        return (
            f"ExampleDataConfig(\n"
            f"  n_patients       : {self.n_patients}\n"
            f"  obs_period       : {self.obs_period_start} → {self.obs_period_end}\n"
            f"  events_per_entity: {self.min_events}–{self.max_events}\n"
            f"  event_days       : {self.min_event_days}–{self.max_event_days}\n"
            f"  random_seed      : {self.random_seed}\n"
            f")"
        )


# ══════════════════════════════════════════════════════════════════════════
# Generator
# ══════════════════════════════════════════════════════════════════════════

class ExampleDataGenerator:
    """
    Generates synthetic event and demographics data for eventus vignettes.

    Parameters
    ----------
    config : ExampleDataConfig | None
        Generation and noise configuration. Uses ExampleDataConfig()
        defaults if not provided.

    Examples
    --------
    >>> gen   = ExampleDataGenerator()
    >>> hosp  = gen.generate_events()
    >>> demog = gen.generate_demographics()

    >>> config = ExampleDataConfig.build_from_yaml("example_data_config.yaml")
    >>> gen    = ExampleDataGenerator(config)
    >>> hosp   = gen.generate_events()
    """

    _BAD_DATES = [
        "not-a-date", "99/99/9999", "Jan 32 2020", "2020-13-01",
        "abcdef", "##/##/####", "2020/00/01", "99-99-99",
    ]

    def __init__(self, config: ExampleDataConfig | None = None) -> None:
        if config is None:
            config = ExampleDataConfig()
        if not isinstance(config, ExampleDataConfig):
            raise TypeError(
                f"[ExampleDataGenerator] Error: config must be an "
                f"ExampleDataConfig object, got {type(config).__name__}"
            )
        self._config = config

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate_events(self) -> pd.DataFrame:
        """
        Generate synthetic event data with injected noise.

        Entities with zero events do not appear in the output —
        consistent with real claims files where non-utilizers are absent.

        Returns
        -------
        pd.DataFrame
            Columns: entity_id, start_date, end_date, hospital_id, drg_code
            Shuffled. Contains intentional errors per config.
        """
        cfg = self._config
        rng = np.random.default_rng(cfg.random_seed)

        obs_start = pd.Timestamp(cfg.obs_period_start)
        obs_end   = pd.Timestamp(cfg.obs_period_end)
        obs_days  = (obs_end - obs_start).days

        # ── Clean rows ────────────────────────────────────────────────────
        rows = []
        for pid in range(1, cfg.n_patients + 1):
            n_events = int(rng.integers(cfg.min_events, cfg.max_events + 1))
            for _ in range(n_events):
                start    = obs_start + pd.Timedelta(
                    days=int(rng.integers(0, obs_days))
                )
                duration = int(rng.integers(cfg.min_event_days, cfg.max_event_days + 1))
                end      = min(start + pd.Timedelta(days=duration), obs_end)
                rows.append({
                    "entity_id":  f"P{pid:04d}",
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date":   end.strftime("%Y-%m-%d"),
                    "hospital_id": f"H{rng.integers(1, 11):02d}",
                    "drg_code":   f"DRG{rng.integers(100, 999):03d}",
                })

        n_clean     = len(rows)
        n_patients  = cfg.n_patients
        all_pids    = [f"P{i:04d}" for i in range(1, n_patients + 1)]

        def _n_noise(frac: float, level: str) -> int:
            """Compute number of noise rows from fraction and level."""
            if level == "row":
                return max(1, round(frac * n_clean))
            else:  # patient
                return max(1, round(frac * n_patients))

        def _rand_pid() -> str:
            return f"P{rng.integers(1, n_patients + 1):04d}"

        def _rand_date() -> str:
            return (obs_start + pd.Timedelta(
                days=int(rng.integers(0, obs_days))
            )).strftime("%Y-%m-%d")

        def _rand_hosp() -> str:
            return f"H{rng.integers(1, 11):02d}"

        def _rand_drg() -> str:
            return f"DRG{rng.integers(100, 999):03d}"

        def _rand_end(start_str: str, max_days: int = 15) -> str:
            return (pd.Timestamp(start_str) + pd.Timedelta(
                days=int(rng.integers(1, max_days))
            )).strftime("%Y-%m-%d")

        # ── Null entity IDs ───────────────────────────────────────────────
        n = _n_noise(cfg.frac_null_entity_ids, cfg.null_entity_ids_level)
        pids = list(rng.choice(all_pids, n, replace=False)) \
            if cfg.null_entity_ids_level == "patient" else [None] * n
        for pid in pids:
            d = _rand_date()
            rows.append({
                "entity_id":   None if cfg.null_entity_ids_level == "patient" else None,
                "start_date":  d,
                "end_date":    _rand_end(d),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Null start dates ──────────────────────────────────────────────
        n = _n_noise(cfg.frac_null_start_dates, cfg.null_start_dates_level)
        for _ in range(n):
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  None,
                "end_date":    _rand_date(),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Null end dates ────────────────────────────────────────────────
        n = _n_noise(cfg.frac_null_end_dates, cfg.null_end_dates_level)
        for _ in range(n):
            d = _rand_date()
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  d,
                "end_date":    None,
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Unparseable dates ─────────────────────────────────────────────
        n = _n_noise(cfg.frac_unparseable_dates, cfg.unparseable_dates_level)
        for i in range(n):
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  self._BAD_DATES[i % len(self._BAD_DATES)],
                "end_date":    _rand_date(),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Before floor ──────────────────────────────────────────────────
        n = _n_noise(cfg.frac_before_floor, cfg.before_floor_level)
        for _ in range(n):
            start = pd.Timestamp("1800-01-01") + pd.Timedelta(
                days=int(rng.integers(0, 43000))
            )
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  start.strftime("%Y-%m-%d"),
                "end_date":    (start + pd.Timedelta(
                    days=int(rng.integers(1, 15))
                )).strftime("%Y-%m-%d"),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── After ceiling ─────────────────────────────────────────────────
        n = _n_noise(cfg.frac_after_ceiling, cfg.after_ceiling_level)
        for _ in range(n):
            start = pd.Timestamp("2101-01-01") + pd.Timedelta(
                days=int(rng.integers(0, 3650))
            )
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  start.strftime("%Y-%m-%d"),
                "end_date":    (start + pd.Timedelta(
                    days=int(rng.integers(1, 15))
                )).strftime("%Y-%m-%d"),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Causality violations ──────────────────────────────────────────
        n = _n_noise(cfg.frac_causality_violations, cfg.causality_violations_level)
        for _ in range(n):
            end   = obs_start + pd.Timedelta(days=int(rng.integers(0, obs_days)))
            start = end + pd.Timedelta(days=int(rng.integers(1, 20)))
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  start.strftime("%Y-%m-%d"),
                "end_date":    end.strftime("%Y-%m-%d"),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Duplicates ────────────────────────────────────────────────────
        n = _n_noise(cfg.frac_duplicates, cfg.duplicates_level)
        if n_clean > 0:
            sample_idx = rng.integers(0, n_clean, n)
            for i in sample_idx:
                rows.append(dict(rows[i]))

        # ── Timestamps ────────────────────────────────────────────────────
        n = _n_noise(cfg.frac_timestamps, cfg.timestamps_level)
        for _ in range(n):
            start = obs_start + pd.Timedelta(days=int(rng.integers(0, obs_days)))
            end   = start + pd.Timedelta(days=int(rng.integers(1, 15)))
            h1, m1 = int(rng.integers(0, 24)), int(rng.integers(0, 60))
            h2, m2 = int(rng.integers(0, 24)), int(rng.integers(0, 60))
            rows.append({
                "entity_id":   _rand_pid(),
                "start_date":  f"{start.strftime('%Y-%m-%d')} {h1:02d}:{m1:02d}",
                "end_date":    f"{end.strftime('%Y-%m-%d')} {h2:02d}:{m2:02d}",
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        # ── Overlapping pairs (always patient-level) ──────────────────────
        n = max(1, round(cfg.frac_overlapping_pairs * n_patients))
        for _ in range(n):
            pid  = _rand_pid()
            base = obs_start + pd.Timedelta(
                days=int(rng.integers(0, max(obs_days - 14, 1)))
            )
            rows.append({
                "entity_id":   pid,
                "start_date":  base.strftime("%Y-%m-%d"),
                "end_date":    (base + pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })
            overlap_start = base + pd.Timedelta(days=int(rng.integers(3, 7)))
            rows.append({
                "entity_id":   pid,
                "start_date":  overlap_start.strftime("%Y-%m-%d"),
                "end_date":    (overlap_start + pd.Timedelta(days=4)).strftime("%Y-%m-%d"),
                "hospital_id": _rand_hosp(),
                "drg_code":    _rand_drg(),
            })

        df = pd.DataFrame(rows)
        return df.sample(frac=1, random_state=cfg.random_seed).reset_index(drop=True)

    def generate_demographics(self) -> pd.DataFrame:
        """
        Generate synthetic demographics for all entities.

        Returns one row per entity — all entities, including those
        with no events in generate_events().

        Returns
        -------
        pd.DataFrame
            Columns: entity_id, date_of_birth, sex
        """
        cfg = self._config
        rng = np.random.default_rng(cfg.random_seed)

        dob_start = pd.Timestamp(f"{cfg.dob_year_min}-01-01")
        dob_end   = pd.Timestamp(f"{cfg.dob_year_max}-12-31")
        dob_days  = (dob_end - dob_start).days

        rows = []
        for pid in range(1, cfg.n_patients + 1):
            dob = dob_start + pd.Timedelta(days=int(rng.integers(0, dob_days)))
            rows.append({
                "entity_id":     f"P{pid:04d}",
                "date_of_birth": dob.strftime("%Y-%m-%d"),
                "sex":           rng.choice(["M", "F"]),
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"ExampleDataGenerator(\n"
            f"  config : {self._config.__class__.__name__}\n"
            f"  seed   : {self._config.random_seed}\n"
            f")"
        )
