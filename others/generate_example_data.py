"""
generate_example_events_data.py
Generates synthetic inpatient hospitalization and patient demographics data
for eventus vignettes.

Edit the CONFIGURATION section at the top to change the generated data.
"""
import numpy as np
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION — edit these to change the generated data
# ══════════════════════════════════════════════════════════════════════════

# Number of unique patients
N_PATIENTS = 50

# Observation period — hospitalizations are generated within this range
OBS_PERIOD_START = "2022-01-01"
OBS_PERIOD_END   = "2022-06-30"

# Hospitalizations per patient — random between these bounds (inclusive)
# MIN_STAYS = 0 means some patients have no hospitalizations and will
# not appear in the hospitalization file at all (realistic)
MIN_STAYS     = 0
MAX_STAYS     = 10

# Stay duration in days — random between these bounds
MIN_STAY_DAYS = 1
MAX_STAY_DAYS = 30

# Birth year range for demographics
DOB_YEAR_MIN = 2000
DOB_YEAR_MAX = 2005

# Random seed — change to get a different dataset
RANDOM_SEED = 42

# ══════════════════════════════════════════════════════════════════════════


def generate_hospitalizations(
    n_patients:       int = N_PATIENTS,
    obs_start:        str = OBS_PERIOD_START,
    obs_end:          str = OBS_PERIOD_END,
    min_stays:        int = MIN_STAYS,
    max_stays:        int = MAX_STAYS,
    min_stay_days:    int = MIN_STAY_DAYS,
    max_stay_days:    int = MAX_STAY_DAYS,
    random_state:     int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Generate synthetic inpatient hospitalization data with intentional
    messiness across all cleaning categories.

    Patients with zero stays do not appear in the output — consistent
    with real claims files where non-utilizers are absent.

    Parameters
    ----------
    n_patients : int
        Number of unique patients.
    obs_start : str
        Start of the observation period (ISO format).
    obs_end : str
        End of the observation period (ISO format).
    min_stays : int
        Minimum hospitalizations per patient (0 = some patients absent).
    max_stays : int
        Maximum hospitalizations per patient.
    min_stay_days : int
        Minimum stay duration in days.
    max_stay_days : int
        Maximum stay duration in days.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Columns: patient_id, admit_date, discharge_date,
                 hospital_id, drg_code
        Includes intentional errors for cleaning vignette.
    """
    rng       = np.random.default_rng(random_state)
    obs_start_ts = pd.Timestamp(obs_start)
    obs_end_ts   = pd.Timestamp(obs_end)
    obs_days     = (obs_end_ts - obs_start_ts).days

    rows = []

    # ── Clean rows ────────────────────────────────────────────────────────
    for pid in range(1, n_patients + 1):
        n_stays = int(rng.integers(min_stays, max_stays + 1))
        for _ in range(n_stays):
            admit = obs_start_ts + pd.Timedelta(
                days=int(rng.integers(0, obs_days))
            )
            duration  = int(rng.integers(min_stay_days, max_stay_days + 1))
            discharge = admit + pd.Timedelta(days=duration)
            # Clip discharge to obs_end
            discharge = min(discharge, obs_end_ts)
            rows.append({
                "patient_id":     f"P{pid:04d}",
                "admit_date":     admit.strftime("%Y-%m-%d"),
                "discharge_date": discharge.strftime("%Y-%m-%d"),
                "hospital_id":    f"H{rng.integers(1, 11):02d}",
                "drg_code":       f"DRG{rng.integers(100, 999):03d}",
            })

    n_clean = len(rows)

    # ── Intentional errors ────────────────────────────────────────────────
    # Scale error counts relative to clean rows
    n_err = max(n_clean // 10, 10)

    def rand_date(offset_days=0):
        return (obs_start_ts + pd.Timedelta(
            days=int(rng.integers(0, obs_days + offset_days))
        )).strftime("%Y-%m-%d")

    def rand_pid():
        return f"P{rng.integers(1, n_patients + 1):04d}"

    def rand_hosp():
        return f"H{rng.integers(1, 11):02d}"

    def rand_drg():
        return f"DRG{rng.integers(100, 999):03d}"

    # Null patient IDs
    for _ in range(max(n_err // 12, 5)):
        d = rand_date()
        rows.append({
            "patient_id":     None,
            "admit_date":     d,
            "discharge_date": (pd.Timestamp(d) +
                               pd.Timedelta(days=int(rng.integers(1, 15))
                               )).strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Null admit dates
    for _ in range(max(n_err // 12, 5)):
        d = rand_date()
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     None,
            "discharge_date": d,
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Null discharge dates
    for _ in range(max(n_err // 12, 5)):
        d = rand_date()
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     d,
            "discharge_date": None,
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Unparseable dates
    bad_dates = [
        "not-a-date", "99/99/9999", "Jan 32 2020", "2020-13-01",
        "abcdef", "##/##/####", "2020/00/01", "99-99-99",
    ]
    for i in range(max(n_err // 15, 4)):
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     bad_dates[i % len(bad_dates)],
            "discharge_date": rand_date(),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Before date floor (implausibly early)
    for _ in range(max(n_err // 15, 4)):
        admit = pd.Timestamp("1800-01-01") + pd.Timedelta(
            days=int(rng.integers(0, 43000))
        )
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     admit.strftime("%Y-%m-%d"),
            "discharge_date": (admit + pd.Timedelta(
                days=int(rng.integers(1, 15))
            )).strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # After date ceiling (implausibly late)
    for _ in range(max(n_err // 15, 4)):
        admit = pd.Timestamp("2101-01-01") + pd.Timedelta(
            days=int(rng.integers(0, 3650))
        )
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     admit.strftime("%Y-%m-%d"),
            "discharge_date": (admit + pd.Timedelta(
                days=int(rng.integers(1, 15))
            )).strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Causality violations (discharge before admit)
    for _ in range(max(n_err // 8, 8)):
        discharge = obs_start_ts + pd.Timedelta(
            days=int(rng.integers(0, obs_days))
        )
        admit = discharge + pd.Timedelta(days=int(rng.integers(1, 20)))
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     admit.strftime("%Y-%m-%d"),
            "discharge_date": discharge.strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Duplicate rows — copy random clean rows
    clean_sample = [rows[i] for i in rng.integers(0, n_clean, max(n_err // 8, 8))]
    rows.extend(clean_sample)

    # Timestamps (need normalization)
    for _ in range(max(n_err // 10, 6)):
        admit = obs_start_ts + pd.Timedelta(days=int(rng.integers(0, obs_days)))
        discharge = admit + pd.Timedelta(days=int(rng.integers(1, 15)))
        h, m = rng.integers(0, 24), rng.integers(0, 60)
        rows.append({
            "patient_id":     rand_pid(),
            "admit_date":     f"{admit.strftime('%Y-%m-%d')} {h:02d}:{m:02d}",
            "discharge_date": f"{discharge.strftime('%Y-%m-%d')} "
                              f"{rng.integers(0,24):02d}:{rng.integers(0,60):02d}",
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Overlapping stays (same patient, adjacent intervals)
    for _ in range(max(n_err // 10, 6)):
        pid  = rand_pid()
        base = obs_start_ts + pd.Timedelta(days=int(rng.integers(0, obs_days - 14)))
        rows.append({
            "patient_id":     pid,
            "admit_date":     base.strftime("%Y-%m-%d"),
            "discharge_date": (base + pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })
        overlap_start = base + pd.Timedelta(days=int(rng.integers(3, 7)))
        rows.append({
            "patient_id":     pid,
            "admit_date":     overlap_start.strftime("%Y-%m-%d"),
            "discharge_date": (overlap_start + pd.Timedelta(days=4)).strftime("%Y-%m-%d"),
            "hospital_id":    rand_hosp(),
            "drg_code":       rand_drg(),
        })

    # Shuffle and return
    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=int(random_state)).reset_index(drop=True)


def generate_patient_demographics(
    n_patients:   int = N_PATIENTS,
    dob_year_min: int = DOB_YEAR_MIN,
    dob_year_max: int = DOB_YEAR_MAX,
    random_state: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Generate synthetic patient demographics for the same patient IDs
    produced by generate_hospitalizations().

    Parameters
    ----------
    n_patients : int
        Must match n_patients in generate_hospitalizations(). Default 750.
    dob_year_min : int
        Earliest birth year. Default 1940.
    dob_year_max : int
        Latest birth year. Default 1980.
    random_state : int
        Random seed for reproducibility. Default 42.

    Returns
    -------
    pd.DataFrame
        Columns: patient_id, date_of_birth, sex
        One row per patient. Same patient IDs as generate_hospitalizations().
    """
    rng = np.random.default_rng(random_state)

    dob_start = pd.Timestamp(f"{dob_year_min}-01-01")
    dob_end   = pd.Timestamp(f"{dob_year_max}-12-31")
    dob_days  = (dob_end - dob_start).days

    rows = []
    for pid in range(1, n_patients + 1):
        dob = dob_start + pd.Timedelta(days=int(rng.integers(0, dob_days)))
        rows.append({
            "patient_id":    f"P{pid:04d}",
            "date_of_birth": dob.strftime("%Y-%m-%d"),
            "sex":           rng.choice(["M", "F"]),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    hosp_df  = generate_hospitalizations()
    demog_df = generate_patient_demographics()

    print(f"Hospitalizations : {len(hosp_df):,} rows")
    print(f"Unique patient IDs in hosp file: "
          f"{hosp_df['patient_id'].nunique()} "
          f"(of {N_PATIENTS} total patients)")
    print(f"Demographics     : {len(demog_df):,} patients")
    print(f"\nSample hospitalizations:")
    print(hosp_df.head())
    print(f"\nSample demographics:")
    print(demog_df.head())
    print(f"\nBirth year range: "
          f"{pd.to_datetime(demog_df['date_of_birth']).dt.year.min()} – "
          f"{pd.to_datetime(demog_df['date_of_birth']).dt.year.max()}")

    hosp_df.to_csv("hospitalizations_raw.csv",   index=False)
    demog_df.to_csv("patient_demographics.csv",  index=False)
    print("\nSaved: hospitalizations_raw.csv, patient_demographics.csv")
