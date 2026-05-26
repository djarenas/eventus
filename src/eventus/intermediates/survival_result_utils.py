"""
survival_result_utils.py
KM survival curve computation utilities for SurvivalResult.
No class state — only data inputs and outputs.

Functions
---------
compute_survival_table(time_to_episode, obs_duration, ci_method)
    Compute a KM survival table from arrays of episode times and
    observation durations (used as censoring times for non-episodes).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

_ERROR = "[survival_result_utils] Error"

_VALID_CI_METHODS = {"greenwood"}


# ------------------------------------------------------------------ #
# Per-entity primitive
# ------------------------------------------------------------------ #

def _time_to_first(
    value:     object,
    obs_start: pd.Timestamp,
    obs_end:   pd.Timestamp,
) -> float:
    """
    Return days from obs_start to first event within the obs window.
    Returns np.nan if value is NaN or no dates fall within the window.

    Intentionally self-contained — does not import from
    event_primitives_utils so that survival_result_utils remains
    reusable outside the event analysis context.
    """
    if pd.isna(value):
        return np.nan
    dates = []
    for token in str(value).split(" | "):
        try:
            ts = pd.Timestamp(token.strip()).normalize()
            if obs_start <= ts <= obs_end:
                dates.append(ts)
        except Exception:
            continue
    if not dates:
        return np.nan
    return float((min(dates) - obs_start).days)


# ------------------------------------------------------------------ #
# KM computation
# ------------------------------------------------------------------ #

def compute_survival_table(
    time_to_episode: np.ndarray,
    obs_duration:  np.ndarray,
    ci_method:     str = "greenwood",
) -> pd.DataFrame:
    """
    Compute a Kaplan-Meier survival table.

    Each entity either experienced the episode (has a finite time_to_episode)
    or was censored at their obs_duration (time_to_episode is NaN).

    Parameters
    ----------
    time_to_episode : np.ndarray
        1-D float array. Days from obs_start to first event.
        NaN for entities with no event (censored at obs_duration).
    obs_duration : np.ndarray
        1-D float array. Length of obs period in days per entity.
        Used as the censoring time for entities with NaN time_to_episode.
        Must be same length as time_to_episode.
    ci_method : str
        Confidence interval method. Currently only 'greenwood'.

    Returns
    -------
    pd.DataFrame
        One row per unique episode timepoint. Columns:
        day          (int)   — timepoint in days from obs_start
        n_at_risk    (int)   — entities still under observation
        n_episodes     (int)   — episodes occurring at this timepoint
        n_censored   (int)   — entities censored at this timepoint
        survival     (float) — KM estimate S(t)
        ci_lower     (float) — lower confidence bound
        ci_upper     (float) — upper confidence bound

    Raises
    ------
    ValueError if ci_method is not in _VALID_CI_METHODS.
    ValueError if arrays are not the same length.
    ValueError if any obs_duration is <= 0.
    """
    if ci_method not in _VALID_CI_METHODS:
        raise ValueError(
            f"{_ERROR} ci_method must be one of "
            f"{sorted(_VALID_CI_METHODS)}, got {ci_method!r}"
        )
    if len(time_to_episode) != len(obs_duration):
        raise ValueError(
            f"{_ERROR} time_to_episode and obs_duration must be the same "
            f"length, got {len(time_to_episode)} and {len(obs_duration)}"
        )
    if np.any(obs_duration <= 0):
        n_bad = int(np.sum(obs_duration <= 0))
        raise ValueError(
            f"{_ERROR} obs_duration must be > 0 for all entities. "
            f"Found {n_bad} entity/entities with obs_duration <= 0."
        )

    n_total = len(time_to_episode)

    # Build per-entity records: (time, is_episode)
    # Censored entities use obs_duration as their time
    times    = np.where(np.isnan(time_to_episode), obs_duration, time_to_episode)
    is_episode = ~np.isnan(time_to_episode)

    # Collect unique episode timepoints only — censoring alone does not
    # produce a KM step
    episode_times = np.unique(times[is_episode])

    if len(episode_times) == 0:
        # No episodes at all — survival stays at 1.0 throughout
        return pd.DataFrame({
            "day":        pd.array([], dtype=int),
            "n_at_risk":  pd.array([], dtype=int),
            "n_episodes":   pd.array([], dtype=int),
            "n_censored": pd.array([], dtype=int),
            "survival":   pd.array([], dtype=float),
            "ci_lower":   pd.array([], dtype=float),
            "ci_upper":   pd.array([], dtype=float),
        })

    rows         = []
    survival     = 1.0
    greenwood_sum = 0.0  # cumulative Greenwood sum for CI

    for t in episode_times:
        # n_at_risk = entities whose time >= t
        n_at_risk = int(np.sum(times >= t))

        # n_episodes = entities with an episode exactly at t
        n_episodes = int(np.sum(is_episode & (times == t)))

        # n_censored = entities censored exactly at t
        # (censored at same time as episode — censored after by convention)
        n_censored = int(np.sum(~is_episode & (times == t)))

        # KM step
        if n_at_risk > 0 and n_episodes > 0:
            survival = survival * (1.0 - n_episodes / n_at_risk)

        # Greenwood variance accumulation
        # var(S(t)) = S(t)^2 * sum(d_i / (n_i * (n_i - d_i)))
        if n_at_risk > n_episodes:
            greenwood_sum += n_episodes / (n_at_risk * (n_at_risk - n_episodes))

        greenwood_se = survival * np.sqrt(greenwood_sum)
        z            = 1.96  # 95% CI
        ci_lower     = max(0.0, survival - z * greenwood_se)
        ci_upper     = min(1.0, survival + z * greenwood_se)

        rows.append({
            "day":        int(t),
            "n_at_risk":  n_at_risk,
            "n_episodes":   n_episodes,
            "n_censored": n_censored,
            "survival":   round(float(survival), 6),
            "ci_lower":   round(float(ci_lower),  6),
            "ci_upper":   round(float(ci_upper),  6),
        })

    return pd.DataFrame(rows)


def compute_summary_stats(
    time_to_episode: np.ndarray,
    obs_duration:  np.ndarray,
) -> dict:
    """
    Compute scalar summary statistics for a SurvivalResult __repr__.

    Parameters
    ----------
    time_to_episode : np.ndarray
        Days to first event. NaN = censored.
    obs_duration : np.ndarray
        Observation duration per entity in days.

    Returns
    -------
    dict with keys:
        n_total, n_episodes, n_censored,
        median_survival (float | None),
        episode_rate_pct (float)
    """
    n_total    = len(time_to_episode)
    n_episodes   = int(np.sum(~np.isnan(time_to_episode)))
    n_censored = n_total - n_episodes

    # Median survival = smallest t where S(t) <= 0.5
    # Computed from the episode times directly
    episode_times   = np.sort(time_to_episode[~np.isnan(time_to_episode)])
    median_survival: float | None = None
    if len(episode_times) > 0:
        survival = 1.0
        for i, t in enumerate(episode_times):
            n_at_risk = n_total - i
            survival  = survival * (1.0 - 1.0 / n_at_risk)
            if survival <= 0.5:
                median_survival = float(t)
                break

    return {
        "n_total":          n_total,
        "n_episodes":         n_episodes,
        "n_censored":       n_censored,
        "median_survival":  median_survival,
        "episode_rate_pct":   round(100 * n_episodes / n_total, 1) if n_total else 0.0,
    }
