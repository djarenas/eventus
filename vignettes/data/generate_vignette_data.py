"""
generate_vignette_data.py
Synthetic data generator for eventus vignettes.

Produces a fixed hospitalization claims DataFrame with known properties
for use in the vignette series. All properties are deterministic given
the seed — running this script always produces identical output.

Properties
----------
Total rows        : 10,000
Unique patients   : 500
Null patient IDs  : ~100  (1.0%)
Null admit dates  : ~300  (3.0%)
Implausible dates : 2     (1 before floor, 1 after ceiling)
Causality violations : ~50  (0.5%) — discharge before admit
Exact duplicates  : ~1,500 (15.0%)
Overlapping stays : ~10% of patients have at least one transfer
Date range        : 2020-01-01 to 2022-12-31
hospital_id       : Hospital_A (50%), Hospital_B (30%), Hospital_C (20%)
icd10_condition   : conditionA / conditionB / conditionC, ~10% nulls

Usage
-----
From the repo root:

    python vignettes/data/generate_vignette_data.py

    Or from Python:
        from generate_vignette_data import make_hospitalization_data
        df = make_hospitalization_data()

Output
------
    vignettes/data/hospitalization_claims.csv
    vignettes/data/ed_visits.csv
"""
from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

SEED            = 42
N_PATIENTS      = 800
N_ROWS_TARGET   = 10_000
DATE_START      = pd.Timestamp("2020-01-01")
DATE_END        = pd.Timestamp("2022-12-31")
OBS_START       = pd.Timestamp("2022-01-01")
OBS_END         = pd.Timestamp("2022-12-31")

HOSPITAL_IDS    = ["Hospital_A", "Hospital_B", "Hospital_C"]
HOSPITAL_PROBS  = [0.50,          0.30,          0.20]

CONDITIONS      = ["conditionA", "conditionB", "conditionC"]
CONDITION_PROBS = [0.45,          0.35,          0.20]
CONDITION_NULL_RATE = 0.10

NULL_PATIENT_ID_RATE  = 0.01
NULL_ADMIT_DATE_RATE  = 0.03
DUPLICATE_RATE        = 0.15
CAUSALITY_VIOLATION_RATE = 0.005
N_IMPLAUSIBLE         = 2

# ED visit properties
N_ED_ROWS_TARGET  = 5_000
ED_NULL_PATIENT_RATE = 0.01
ED_NULL_DATE_RATE    = 0.02
ED_DUPLICATE_RATE    = 0.08

# Nursing facility properties
N_NF_RESIDENTS    = 200
NF_FACILITY_IDS   = ["Facility_A", "Facility_B"]
NF_FACILITY_PROBS = [0.60, 0.40]
NF_MOBILITY       = ["independent", "assisted", "dependent"]
NF_NULL_RATE      = 0.05   # nulls in clinical measurements

# Medicaid coverage properties
COVERAGE_DATE_START = pd.Timestamp("2021-01-01")
COVERAGE_DATE_END   = pd.Timestamp("2022-12-31")

# Age window coverage properties
AGE_COVERAGE_START  = pd.Timestamp("2018-01-01")
AGE_COVERAGE_END    = pd.Timestamp("2025-12-31")

# Age window ED visit properties
ED_AGE_ANNUAL_RATE  = 1.0   # Poisson lambda — expected ED visits per year



# ── Hospitalization generator ─────────────────────────────────────────────────

def make_hospitalization_data(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic hospitalization claims with known properties.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility. Default 42.

    Returns
    -------
    pd.DataFrame
        Columns: patient_id, admit_date, discharge_date,
                 hospital_id, icd10_condition
    """
    rng = np.random.default_rng(seed)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

    # ── Base clean stays ──────────────────────────────────────────────────────
    # Each patient gets 1-5 base stays, spread across 2020-2022
    rows = []
    for pid in patient_ids:
        n_stays = rng.integers(1, 6)
        for _ in range(n_stays):
            admit = DATE_START + pd.Timedelta(
                days=int(rng.integers(0, (DATE_END - DATE_START).days - 14))
            )
            duration = int(rng.integers(1, 15))   # 1-14 day stays
            discharge = admit + pd.Timedelta(days=duration)
            if discharge > DATE_END:
                discharge = DATE_END

            hospital = rng.choice(HOSPITAL_IDS, p=HOSPITAL_PROBS)

            condition = (
                rng.choice(CONDITIONS, p=CONDITION_PROBS)
                if rng.random() > CONDITION_NULL_RATE
                else None
            )

            rows.append({
                "patient_id":      pid,
                "admit_date":      admit,
                "discharge_date":  discharge,
                "hospital_id":     hospital,
                "icd10_condition": condition,
            })

    base_df = pd.DataFrame(rows)

    # ── Overlapping stays (~10% of patients) ──────────────────────────────────
    # Pick ~50 patients and add a transfer row that overlaps their last stay
    overlap_patients = rng.choice(patient_ids, size=50, replace=False)
    overlap_rows = []
    for pid in overlap_patients:
        patient_rows = base_df[base_df["patient_id"] == pid]
        if patient_rows.empty:
            continue
        last_row   = patient_rows.iloc[-1]
        # New stay starts 1-2 days before the last discharge — creates overlap
        new_admit  = last_row["discharge_date"] - pd.Timedelta(
            days=int(rng.integers(1, 3))
        )
        new_discharge = new_admit + pd.Timedelta(days=int(rng.integers(1, 5)))
        if new_discharge > DATE_END:
            new_discharge = DATE_END

        overlap_rows.append({
            "patient_id":      pid,
            "admit_date":      new_admit,
            "discharge_date":  new_discharge,
            "hospital_id":     last_row["hospital_id"],
            "icd10_condition": last_row["icd10_condition"],
        })

    if overlap_rows:
        base_df = pd.concat(
            [base_df, pd.DataFrame(overlap_rows)], ignore_index=True
        )

    # ── Expand to target row count via billing-day duplication ────────────────
    # Each stay generates multiple billing rows (one per day of stay)
    # This simulates the raw claims file structure
    billing_rows = []
    for _, row in base_df.iterrows():
        duration = max(1, (row["discharge_date"] - row["admit_date"]).days)
        n_billing = min(duration, int(rng.integers(1, duration + 2)))
        for _ in range(n_billing):
            billing_rows.append(row.to_dict())

    df = pd.DataFrame(billing_rows)

    # Trim or pad to target
    if len(df) > N_ROWS_TARGET:
        df = df.sample(n=N_ROWS_TARGET, random_state=seed).reset_index(drop=True)
    elif len(df) < N_ROWS_TARGET:
        # Pad with duplicates of random rows
        extra = df.sample(
            n=N_ROWS_TARGET - len(df), replace=True, random_state=seed
        )
        df = pd.concat([df, extra], ignore_index=True)

    df = df.reset_index(drop=True)

    # ── Exact duplicates (~15%) ───────────────────────────────────────────────
    n_dupes = int(N_ROWS_TARGET * DUPLICATE_RATE)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    dupes    = df.iloc[dupe_idx].copy()
    df       = pd.concat([df, dupes], ignore_index=True)

    # ── Causality violations (~0.5%) ─────────────────────────────────────────
    n_causal = int(len(df) * CAUSALITY_VIOLATION_RATE)
    causal_idx = rng.choice(len(df), size=n_causal, replace=False)
    for idx in causal_idx:
        admit     = df.at[idx, "admit_date"]
        discharge = df.at[idx, "discharge_date"]
        # Swap them — discharge now before admit
        df.at[idx, "admit_date"]     = discharge
        df.at[idx, "discharge_date"] = admit

    # ── Implausible dates (2 rows) ────────────────────────────────────────────
    df.at[0, "admit_date"]     = pd.Timestamp("1899-06-15")
    df.at[0, "discharge_date"] = pd.Timestamp("1899-06-20")
    df.at[1, "admit_date"]     = pd.Timestamp("2090-03-01")
    df.at[1, "discharge_date"] = pd.Timestamp("2090-03-05")

    # ── Null admit dates (~3%) ────────────────────────────────────────────────
    n_null_admit = int(len(df) * NULL_ADMIT_DATE_RATE)
    null_admit_idx = rng.choice(len(df), size=n_null_admit, replace=False)
    df.loc[null_admit_idx, "admit_date"] = pd.NaT

    # ── Null patient IDs (~1%) ────────────────────────────────────────────────
    n_null_pid = int(len(df) * NULL_PATIENT_ID_RATE)
    null_pid_idx = rng.choice(len(df), size=n_null_pid, replace=False)
    df.loc[null_pid_idx, "patient_id"] = None

    # ── Format dates as strings (as they would appear in a data warehouse) ────
    df["admit_date"]     = df["admit_date"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )
    df["discharge_date"] = df["discharge_date"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── ED visit generator ────────────────────────────────────────────────────────

def make_ed_visit_data(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic ED visit data with known properties.

    Properties
    ----------
    Columns       : patient_id, ed_visit_date, hospital_id,
                    icd10_condition, systolic_bp
    Visits        : 0-8 per patient across 2020-2022
    hospital_id   : Hospital_A (50%), Hospital_B (30%), Hospital_C (20%)
    icd10_condition: conditionA/B/C, ~10% nulls
    systolic_bp   : numeric ~120 ± 20, ~5% nulls
    Same-date same-hospital records: ~5% of patients have a same-day
      same-hospital record with different descriptor values — these
      are candidates for consolidation.
    Same-date different-hospital records: ~3% of patients visit two
      different hospitals on the same day — these must NOT be
      consolidated (also_defined_by = ["hospital_id"]).
    Exact duplicates: ~8%
    Null patient IDs: ~1%
    Null visit dates: ~2%
    """
    rng = np.random.default_rng(seed + 1)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

    conditions     = ["conditionA", "conditionB", "conditionC"]
    condition_probs = [0.45, 0.35, 0.20]

    rows = []
    for pid in patient_ids:
        n_visits = int(rng.integers(0, 9))
        for _ in range(n_visits):
            visit_date = DATE_START + pd.Timedelta(
                days=int(rng.integers(0, (DATE_END - DATE_START).days))
            )
            hospital = rng.choice(HOSPITAL_IDS, p=HOSPITAL_PROBS)
            condition = (
                rng.choice(conditions, p=condition_probs)
                if rng.random() > 0.10 else None
            )
            systolic_bp = (
                round(float(rng.normal(120, 20)), 1)
                if rng.random() > 0.05 else None
            )
            rows.append({
                "patient_id":      pid,
                "ed_visit_date":   visit_date,
                "hospital_id":     hospital,
                "icd10_condition": condition,
                "systolic_bp":     systolic_bp,
            })

    df = pd.DataFrame(rows)

    # Trim or pad to target
    if len(df) > N_ED_ROWS_TARGET:
        df = df.sample(n=N_ED_ROWS_TARGET, random_state=seed).reset_index(drop=True)
    elif len(df) < N_ED_ROWS_TARGET:
        extra = df.sample(
            n=N_ED_ROWS_TARGET - len(df), replace=True, random_state=seed
        )
        df = pd.concat([df, extra], ignore_index=True)

    df = df.reset_index(drop=True)

    # ── Same-date same-hospital records (~5% of patients) ─────────────────────
    # Same patient, same date, same hospital, different descriptor values.
    # These are candidates for consolidation.
    consolidate_patients = rng.choice(patient_ids, size=int(N_PATIENTS * 0.05), replace=False)
    consolidate_rows = []
    for pid in consolidate_patients:
        patient_rows = df[df["patient_id"] == pid]
        if patient_rows.empty:
            continue
        base_row = patient_rows.iloc[0]
        consolidate_rows.append({
            "patient_id":      pid,
            "ed_visit_date":   base_row["ed_visit_date"],
            "hospital_id":     base_row["hospital_id"],
            "icd10_condition": rng.choice(conditions, p=condition_probs),
            "systolic_bp":     round(float(rng.normal(120, 20)), 1),
        })
    if consolidate_rows:
        df = pd.concat([df, pd.DataFrame(consolidate_rows)], ignore_index=True)

    # ── Same-date different-hospital records (~3% of patients) ────────────────
    # Same patient, same date, different hospital.
    # These must NOT be consolidated — hospital_id is in also_defined_by.
    multi_hosp_patients = rng.choice(patient_ids, size=int(N_PATIENTS * 0.03), replace=False)
    multi_hosp_rows = []
    for pid in multi_hosp_patients:
        patient_rows = df[df["patient_id"] == pid]
        if patient_rows.empty:
            continue
        base_row  = patient_rows.iloc[0]
        other_hospitals = [h for h in HOSPITAL_IDS if h != base_row["hospital_id"]]
        if not other_hospitals:
            continue
        multi_hosp_rows.append({
            "patient_id":      pid,
            "ed_visit_date":   base_row["ed_visit_date"],
            "hospital_id":     rng.choice(other_hospitals),
            "icd10_condition": rng.choice(conditions, p=condition_probs),
            "systolic_bp":     round(float(rng.normal(120, 20)), 1),
        })
    if multi_hosp_rows:
        df = pd.concat([df, pd.DataFrame(multi_hosp_rows)], ignore_index=True)

    # ── Exact duplicates (~8%) ────────────────────────────────────────────────
    n_dupes  = int(len(df) * ED_DUPLICATE_RATE)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    df       = pd.concat([df, df.iloc[dupe_idx].copy()], ignore_index=True)

    # ── Null patient IDs (~1%) ────────────────────────────────────────────────
    n_null_pid = int(len(df) * ED_NULL_PATIENT_RATE)
    null_pid_idx = rng.choice(len(df), size=n_null_pid, replace=False)
    df.loc[null_pid_idx, "patient_id"] = None

    # ── Null visit dates (~2%) ────────────────────────────────────────────────
    n_null_date = int(len(df) * ED_NULL_DATE_RATE)
    null_date_idx = rng.choice(len(df), size=n_null_date, replace=False)
    df.loc[null_date_idx, "ed_visit_date"] = pd.NaT

    # ── Format dates as strings ───────────────────────────────────────────────
    df["ed_visit_date"] = df["ed_visit_date"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── Nursing facility generator ────────────────────────────────────────────────

def make_nursing_facility_data(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic nursing facility assessment data.

    Each resident has one stay of 60-180 days with monthly assessments.
    ~15% of residents have two stays (readmission after a gap).
    Each assessment row records systolic_bp, bmi, and mobility_status.

    Properties
    ----------
    Residents         : 200
    Facilities        : Facility_A (60%), Facility_B (40%)
    Assessments       : every ~30 days per stay (2-6 per resident)
    systolic_bp       : numeric, ~120 ± 20, ~5% nulls
    bmi               : numeric, ~25 ± 4, ~5% nulls
    mobility_status   : category (independent/assisted/dependent), ~5% nulls
    Duplicate rows    : ~5%
    """
    rng = np.random.default_rng(seed + 2)

    resident_ids = [f"NF{str(i).zfill(4)}" for i in range(1, N_NF_RESIDENTS + 1)]
    rows = []

    for rid in resident_ids:
        facility = rng.choice(NF_FACILITY_IDS, p=NF_FACILITY_PROBS)

        # Primary stay — 60 to 180 days
        admit = DATE_START + pd.Timedelta(
            days=int(rng.integers(0, (DATE_END - DATE_START).days - 180))
        )
        stay_days = int(rng.integers(60, 181))
        discharge = admit + pd.Timedelta(days=stay_days)

        # Starting clinical values
        bp_base       = float(rng.normal(120, 15))
        bmi_base      = float(rng.normal(25, 4))
        mobility_idx  = int(rng.integers(0, 3))

        # Monthly assessments
        assessment_date = admit
        while assessment_date <= discharge:
            # Slight drift in clinical values over time
            bp  = bp_base  + float(rng.normal(0, 5))
            bmi = bmi_base + float(rng.normal(0, 0.5))

            # Mobility can worsen over time (small probability of decline)
            if rng.random() < 0.1 and mobility_idx < 2:
                mobility_idx += 1
            mobility = NF_MOBILITY[mobility_idx]

            rows.append({
                "resident_id":    rid,
                "facility_id":    facility,
                "admit_date":     admit,
                "discharge_date": discharge,
                "assessment_date": assessment_date,
                "systolic_bp":    round(bp, 1),
                "bmi":            round(bmi, 1),
                "mobility_status": mobility,
            })
            assessment_date = assessment_date + pd.Timedelta(days=30)

        # ~15% chance of a second stay after a gap
        if rng.random() < 0.15:
            gap        = int(rng.integers(14, 60))
            admit2     = discharge + pd.Timedelta(days=gap)
            stay2_days = int(rng.integers(30, 120))
            discharge2 = admit2 + pd.Timedelta(days=stay2_days)
            if discharge2 > DATE_END:
                discharge2 = DATE_END

            assessment_date = admit2
            while assessment_date <= discharge2:
                bp  = bp_base  + float(rng.normal(0, 5))
                bmi = bmi_base + float(rng.normal(0, 0.5))
                if rng.random() < 0.1 and mobility_idx < 2:
                    mobility_idx += 1
                mobility = NF_MOBILITY[mobility_idx]

                rows.append({
                    "resident_id":    rid,
                    "facility_id":    facility,
                    "admit_date":     admit2,
                    "discharge_date": discharge2,
                    "assessment_date": assessment_date,
                    "systolic_bp":    round(bp, 1),
                    "bmi":            round(bmi, 1),
                    "mobility_status": mobility,
                })
                assessment_date = assessment_date + pd.Timedelta(days=30)

    df = pd.DataFrame(rows)

    # ── Introduce nulls (~5%) in clinical columns ─────────────────────────────
    for col in ["systolic_bp", "bmi", "mobility_status"]:
        null_idx = rng.choice(len(df), size=int(len(df) * NF_NULL_RATE), replace=False)
        df.loc[null_idx, col] = None

    # ── Exact duplicates (~5%) ────────────────────────────────────────────────
    n_dupes  = int(len(df) * 0.05)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    dupes    = df.iloc[dupe_idx].copy()
    df       = pd.concat([df, dupes], ignore_index=True)

    # ── Format dates as strings ───────────────────────────────────────────────
    for col in ["admit_date", "discharge_date", "assessment_date"]:
        df[col] = df[col].apply(
            lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
        )

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── Medicaid coverage generator ──────────────────────────────────────────────

def make_medicaid_coverage_data(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic Medicaid coverage data.

    Each member has 1-3 coverage periods across 2021-2022.
    Coverage patterns:
      ~15% fully covered — exactly Jan 1 to Dec 31
      ~55% continuously covered for most of 2022 (late start or early exit)
      ~20% have one gap — enrolled, lapse, re-enroll
      ~10% partially covered — only part of 2022

    Properties
    ----------
    Members           : 500 (same patient_id pool as hospitalizations)
    Coverage periods  : 1-3 per member
    Date range        : 2021-01-01 to 2022-12-31
    Duplicate rows    : ~3%
    Null dates        : ~1%
    """
    rng = np.random.default_rng(seed + 3)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]
    rows = []

    for pid in patient_ids:
        pattern = rng.choice(
            ["full", "continuous", "one_gap", "partial"],
            p=[0.15, 0.55, 0.20, 0.10],
        )

        if pattern == "full":
            # Exactly Jan 1 to Dec 31 — full year coverage
            rows.append({
                "patient_id":     pid,
                "coverage_start": pd.Timestamp("2022-01-01"),
                "coverage_end":   pd.Timestamp("2022-12-31"),
            })

        elif pattern == "continuous":
            # One long coverage period covering most of 2022
            start = pd.Timestamp("2022-01-01") + pd.Timedelta(
                days=int(rng.integers(1, 30))
            )
            end = pd.Timestamp("2022-12-31") - pd.Timedelta(
                days=int(rng.integers(1, 30))
            )
            rows.append({
                "patient_id":     pid,
                "coverage_start": start,
                "coverage_end":   end,
            })

        elif pattern == "one_gap":
            # Two coverage periods with a gap in between
            start1 = pd.Timestamp("2022-01-01") + pd.Timedelta(
                days=int(rng.integers(0, 30))
            )
            end1 = start1 + pd.Timedelta(days=int(rng.integers(60, 150)))
            gap  = int(rng.integers(14, 60))
            start2 = end1 + pd.Timedelta(days=gap)
            end2   = pd.Timestamp("2022-12-31") - pd.Timedelta(
                days=int(rng.integers(0, 30))
            )
            if start2 < end2:
                rows.append({
                    "patient_id":     pid,
                    "coverage_start": start1,
                    "coverage_end":   end1,
                })
                rows.append({
                    "patient_id":     pid,
                    "coverage_start": start2,
                    "coverage_end":   end2,
                })

        elif pattern == "partial":
            # Short coverage — only part of the year
            start = pd.Timestamp("2022-01-01") + pd.Timedelta(
                days=int(rng.integers(0, 180))
            )
            end = start + pd.Timedelta(days=int(rng.integers(30, 120)))
            if end > pd.Timestamp("2022-12-31"):
                end = pd.Timestamp("2022-12-31")
            rows.append({
                "patient_id":     pid,
                "coverage_start": start,
                "coverage_end":   end,
            })

    df = pd.DataFrame(rows)

    # ── Exact duplicates (~3%) ────────────────────────────────────────────────
    n_dupes  = int(len(df) * 0.03)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    dupes    = df.iloc[dupe_idx].copy()
    df       = pd.concat([df, dupes], ignore_index=True)

    # ── Null dates (~1%) ──────────────────────────────────────────────────────
    n_null = int(len(df) * 0.01)
    null_idx = rng.choice(len(df), size=n_null, replace=False)
    df.loc[null_idx, "coverage_start"] = pd.NaT

    # ── Format dates as strings ───────────────────────────────────────────────
    df["coverage_start"] = df["coverage_start"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )
    df["coverage_end"] = df["coverage_end"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── Member demographics generator ────────────────────────────────────────────

def make_member_demographics(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic member demographics with a mixed DOB distribution.
    Used in Chapter 7 scenario 1 to deliberately demonstrate the
    ObsPeriodPerEntity future-period warning.

    DOB distribution across 800 members:
      ~320 members — DOB 1997-2000 — full or partial 18-21 window in data
      ~240 members — DOB 2001-2004 — window starts mid-data
      ~128 members — DOB 1990-1996 — too old, window ended before 2018
      ~112 members — DOB 2005-2008 — too young, window hasn't started by 2025

    primary_condition — conditionA / conditionB / conditionC (~equal thirds)
    Used in signal simulation to generate condition-dependent visit rates.

    Columns: patient_id, date_of_birth, primary_condition
    """
    rng = np.random.default_rng(seed + 4)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

    # Assign DOB groups
    groups = rng.choice(
        ["full_window", "late_start", "too_old", "too_young"],
        size = N_PATIENTS,
        p    = [0.40, 0.30, 0.16, 0.14],
    )

    # Assign primary conditions — equal thirds
    primary_conditions = rng.choice(
        ["conditionA", "conditionB", "conditionC"],
        size = N_PATIENTS,
        p    = [1/3, 1/3, 1/3],
    )

    rows = []
    for pid, group, condition in zip(patient_ids, groups, primary_conditions):
        if group == "full_window":
            dob_year = int(rng.integers(1997, 2001))
        elif group == "late_start":
            dob_year = int(rng.integers(2001, 2005))
        elif group == "too_old":
            dob_year = int(rng.integers(1990, 1997))
        else:
            dob_year = int(rng.integers(2005, 2009))

        dob_month = int(rng.integers(1, 13))
        dob_day   = int(rng.integers(1, 29))

        rows.append({
            "patient_id":        pid,
            "date_of_birth":     pd.Timestamp(f"{dob_year}-{dob_month:02d}-{dob_day:02d}"),
            "primary_condition": condition,
        })

    df = pd.DataFrame(rows)
    df["date_of_birth"] = df["date_of_birth"].dt.strftime("%Y-%m-%d")
    return df


def make_member_demographics_age18_21(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic member demographics where ALL members have a
    date of birth that places their 18-21 observation window entirely
    in the past relative to the simulation date.

    All 800 members born 1995-2003 — their 18th birthday falls between
    2013 and 2021, and their 21st between 2016 and 2024. No future
    observation periods. No warnings.

    Used in Chapters 4-7 for all age-window analyses.
    Chapter 7 also uses ch04_07_member_demographics_mixed_dob.csv
    to deliberately demonstrate the ObsPeriodPerEntity future-period warning.

    Columns: patient_id, date_of_birth, primary_condition
    """
    rng = np.random.default_rng(seed + 10)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

    primary_conditions = rng.choice(
        ["conditionA", "conditionB", "conditionC"],
        size = N_PATIENTS,
        p    = [1/3, 1/3, 1/3],
    )

    rows = []
    for pid, condition in zip(patient_ids, primary_conditions):
        # All DOBs 1995-2003 — 18-21 window entirely in 2013-2024
        dob_year  = int(rng.integers(1995, 2004))
        dob_month = int(rng.integers(1, 13))
        dob_day   = int(rng.integers(1, 29))

        rows.append({
            "patient_id":        pid,
            "date_of_birth":     pd.Timestamp(f"{dob_year}-{dob_month:02d}-{dob_day:02d}"),
            "primary_condition": condition,
        })

    df = pd.DataFrame(rows)
    df["date_of_birth"] = df["date_of_birth"].dt.strftime("%Y-%m-%d")
    return df


# ── Age window coverage generator ─────────────────────────────────────────────

def make_medicaid_coverage_age_window(seed: int = SEED) -> pd.DataFrame:
    """
    Generate synthetic Medicaid coverage data across 2018-2025.

    Same 500 members as hospitalization data. Coverage periods spread
    across the full 8-year window. Members may have 1-4 coverage periods
    with gaps, lapses, and re-enrollments.

    Columns: patient_id, coverage_start, coverage_end
    Null dates: ~1%
    Duplicates: ~3%
    """
    rng = np.random.default_rng(seed + 5)

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]
    total_days  = (AGE_COVERAGE_END - AGE_COVERAGE_START).days
    rows        = []

    for pid in patient_ids:
        pattern = rng.choice(
            ["continuous", "one_gap", "two_gaps", "partial"],
            p = [0.40, 0.30, 0.15, 0.15],
        )

        if pattern == "continuous":
            # One long coverage period — most of the 8 years
            start = AGE_COVERAGE_START + pd.Timedelta(
                days=int(rng.integers(0, 180))
            )
            end = AGE_COVERAGE_END - pd.Timedelta(
                days=int(rng.integers(0, 180))
            )
            rows.append({"patient_id": pid, "coverage_start": start, "coverage_end": end})

        elif pattern == "one_gap":
            # Two coverage periods with one gap
            start1 = AGE_COVERAGE_START + pd.Timedelta(days=int(rng.integers(0, 180)))
            end1   = start1 + pd.Timedelta(days=int(rng.integers(365, 1000)))
            gap    = int(rng.integers(30, 180))
            start2 = end1 + pd.Timedelta(days=gap)
            end2   = AGE_COVERAGE_END - pd.Timedelta(days=int(rng.integers(0, 180)))
            if end1 < AGE_COVERAGE_END:
                rows.append({"patient_id": pid, "coverage_start": start1, "coverage_end": end1})
            if start2 < end2 and start2 < AGE_COVERAGE_END:
                rows.append({"patient_id": pid, "coverage_start": start2, "coverage_end": min(end2, AGE_COVERAGE_END)})

        elif pattern == "two_gaps":
            # Three coverage periods with two gaps
            start1 = AGE_COVERAGE_START + pd.Timedelta(days=int(rng.integers(0, 90)))
            end1   = start1 + pd.Timedelta(days=int(rng.integers(365, 700)))
            start2 = end1   + pd.Timedelta(days=int(rng.integers(30, 120)))
            end2   = start2 + pd.Timedelta(days=int(rng.integers(365, 700)))
            start3 = end2   + pd.Timedelta(days=int(rng.integers(30, 120)))
            end3   = AGE_COVERAGE_END - pd.Timedelta(days=int(rng.integers(0, 90)))
            for s, e in [(start1, end1), (start2, end2), (start3, end3)]:
                if s < e and s < AGE_COVERAGE_END:
                    rows.append({"patient_id": pid, "coverage_start": s,
                                 "coverage_end": min(e, AGE_COVERAGE_END)})

        elif pattern == "partial":
            # Short coverage — only a portion of the 8 years
            start = AGE_COVERAGE_START + pd.Timedelta(days=int(rng.integers(0, total_days - 365)))
            end   = start + pd.Timedelta(days=int(rng.integers(180, 730)))
            rows.append({"patient_id": pid, "coverage_start": start,
                         "coverage_end": min(end, AGE_COVERAGE_END)})

    df = pd.DataFrame(rows)

    # ── Exact duplicates (~3%) ────────────────────────────────────────────────
    n_dupes  = int(len(df) * 0.03)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    df       = pd.concat([df, df.iloc[dupe_idx].copy()], ignore_index=True)

    # ── Null dates (~1%) ──────────────────────────────────────────────────────
    null_idx = rng.choice(len(df), size=int(len(df) * 0.01), replace=False)
    df.loc[null_idx, "coverage_start"] = pd.NaT

    # ── Format dates ──────────────────────────────────────────────────────────
    df["coverage_start"] = df["coverage_start"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )
    df["coverage_end"] = df["coverage_end"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── Age window ED visit generator ────────────────────────────────────────────

def _make_ed_visits_agewindow_base(
    rng,
    patient_ids:    list,
    annual_rates:   dict,
    primary_cond:   dict,
    signal:         bool,
) -> pd.DataFrame:
    """
    Shared generator for null and signal age window ED visit datasets.

    Parameters
    ----------
    rng           : numpy random generator
    patient_ids   : list of patient IDs
    annual_rates  : dict mapping patient_id → annual visit rate
    primary_cond  : dict mapping patient_id → primary condition
    signal        : if True, condition assigned from primary_cond 80% of time
                    if False, condition assigned randomly (null simulation)
    """
    conditions  = ["conditionA", "conditionB", "conditionC"]
    total_days  = (AGE_COVERAGE_END - AGE_COVERAGE_START).days
    rows        = []

    for pid in patient_ids:
        rate      = annual_rates[pid]
        n_visits  = int(rng.poisson(rate * total_days / 365.25))
        primary   = primary_cond[pid]

        for _ in range(n_visits):
            visit_date = AGE_COVERAGE_START + pd.Timedelta(
                days=int(rng.integers(0, total_days))
            )
            hospital = rng.choice(HOSPITAL_IDS, p=HOSPITAL_PROBS)

            # Condition assignment
            if rng.random() > 0.10:  # 90% have a condition
                if signal and rng.random() < 0.80:
                    condition = primary   # 80% from primary condition
                else:
                    condition = rng.choice(conditions)  # random
            else:
                condition = None

            systolic_bp = (
                round(float(rng.normal(120, 20)), 1)
                if rng.random() > 0.05 else None
            )
            rows.append({
                "patient_id":      pid,
                "ed_visit_date":   visit_date,
                "hospital_id":     hospital,
                "icd10_condition": condition,
                "systolic_bp":     systolic_bp,
            })

    df = pd.DataFrame(rows)
    return df


def make_ed_visits_agewindow_null(
    demog_df: "pd.DataFrame",
    seed:     int = SEED,
) -> pd.DataFrame:
    """
    Null simulation — all conditions have the same Poisson rate (λ=1/year).
    Condition assigned randomly — no signal in gap distributions by condition.

    Columns: patient_id, ed_visit_date, hospital_id, icd10_condition, systolic_bp
    """
    rng         = np.random.default_rng(seed + 6)
    patient_ids = demog_df["patient_id"].tolist()
    primary_cond = dict(zip(demog_df["patient_id"], demog_df["primary_condition"]))

    # All members get the same rate
    annual_rates = {pid: ED_AGE_ANNUAL_RATE for pid in patient_ids}

    df = _make_ed_visits_agewindow_base(rng, patient_ids, annual_rates, primary_cond, signal=False)

    # Duplicates and nulls
    n_dupes  = int(len(df) * 0.03)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    df       = pd.concat([df, df.iloc[dupe_idx].copy()], ignore_index=True)
    null_idx = rng.choice(len(df), size=int(len(df) * 0.01), replace=False)
    df.loc[null_idx, "ed_visit_date"] = pd.NaT
    df["ed_visit_date"] = df["ed_visit_date"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def make_ed_visits_agewindow_signal(
    demog_df: "pd.DataFrame",
    seed:     int = SEED,
) -> pd.DataFrame:
    """
    Signal simulation — conditions have different Poisson rates:
      conditionA: λ=1.0/year (baseline)
      conditionB: λ=1.5/year (more frequent visits)
      conditionC: λ=2.0/year (most frequent visits)

    Condition on visits assigned from member's primary condition 80% of
    the time — creates a real signal in gap distributions by condition.

    Columns: patient_id, ed_visit_date, hospital_id, icd10_condition, systolic_bp
    """
    rng         = np.random.default_rng(seed + 7)
    patient_ids = demog_df["patient_id"].tolist()
    primary_cond = dict(zip(demog_df["patient_id"], demog_df["primary_condition"]))

    # Rate depends on primary condition
    rate_map = {"conditionA": 1.0, "conditionB": 1.5, "conditionC": 2.0}
    annual_rates = {
        pid: rate_map[primary_cond[pid]]
        for pid in patient_ids
    }

    df = _make_ed_visits_agewindow_base(rng, patient_ids, annual_rates, primary_cond, signal=True)

    # Duplicates and nulls
    n_dupes  = int(len(df) * 0.03)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    df       = pd.concat([df, df.iloc[dupe_idx].copy()], ignore_index=True)
    null_idx = rng.choice(len(df), size=int(len(df) * 0.01), replace=False)
    df.loc[null_idx, "ed_visit_date"] = pd.NaT
    df["ed_visit_date"] = df["ed_visit_date"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ── Summary printer ───────────────────────────────────────────────────────────

def print_data_summary(
    hosp_df:           pd.DataFrame,
    ed_df:             pd.DataFrame,
    nf_df:             pd.DataFrame,
    cov_df:            pd.DataFrame,
    demog_df:          pd.DataFrame,
    demog_correct_df:  pd.DataFrame,
    age_cov_df:        pd.DataFrame,
    ed_null_df:        pd.DataFrame,
    ed_signal_df:      pd.DataFrame,
) -> None:
    """Print a summary of the generated datasets."""
    print("=" * 56)
    print("Synthetic vignette data — summary")
    print("=" * 56)

    print("\nHospitalization claims:")
    print(f"  Total rows          : {len(hosp_df):,}")
    print(f"  Unique patient IDs  : {hosp_df['patient_id'].nunique():,}")
    print(f"  Null patient IDs    : {hosp_df['patient_id'].isna().sum():,}")
    print(f"  Null admit dates    : {hosp_df['admit_date'].isna().sum():,}")

    print("\nED visits (ch01_06_ed_visits.csv):")
    print(f"  Total rows          : {len(ed_df):,}")
    print(f"  Unique patient IDs  : {ed_df['patient_id'].nunique():,}")
    print(f"  Null patient IDs    : {ed_df['patient_id'].isna().sum():,}")
    print(f"  Null visit dates    : {ed_df['ed_visit_date'].isna().sum():,}")
    print(f"  Null icd10_condition: {ed_df['icd10_condition'].isna().sum():,}")
    print(f"  Null systolic_bp    : {ed_df['systolic_bp'].isna().sum():,}")

    print("\nNursing facility assessments:")
    print(f"  Total rows          : {len(nf_df):,}")
    print(f"  Unique residents    : {nf_df['resident_id'].nunique():,}")

    print("\nMedicaid coverage (2021-2022):")
    print(f"  Total rows          : {len(cov_df):,}")
    print(f"  Unique patient IDs  : {cov_df['patient_id'].nunique():,}")
    print(f"  Null coverage_start : {cov_df['coverage_start'].isna().sum():,}")

    print("\nMember demographics:")
    print(f"  Total members       : {len(demog_df):,}")
    dob = pd.to_datetime(demog_df['date_of_birth'], errors='coerce')
    print(f"  Earliest DOB        : {dob.min().date()}")
    print(f"  Latest DOB          : {dob.max().date()}")
    print(f"  conditionA          : {(demog_df['primary_condition']=='conditionA').sum():,}")
    print(f"  conditionB          : {(demog_df['primary_condition']=='conditionB').sum():,}")
    print(f"  conditionC          : {(demog_df['primary_condition']=='conditionC').sum():,}")
    print(f"  (saved as ch04_07_member_demographics.csv)")

    print("\nMember demographics — correct DOB (ch04_07_member_demographics_clean.csv):")
    print(f"  Total members       : {len(demog_correct_df):,}")
    dob2 = pd.to_datetime(demog_correct_df['date_of_birth'], errors='coerce')
    print(f"  Earliest DOB        : {dob2.min().date()}")
    print(f"  Latest DOB          : {dob2.max().date()}")
    print(f"  All windows in past : True — no future-period warnings expected")

    print("\nMedicaid coverage age window (2018-2025):")
    print(f"  Total rows          : {len(age_cov_df):,}")
    print(f"  Unique patient IDs  : {age_cov_df['patient_id'].nunique():,}")
    print(f"  Null coverage_start : {age_cov_df['coverage_start'].isna().sum():,}")

    print("\nED visits age window — null (ch07_ed_visits_agewindow_null.csv):")
    print(f"  Total rows          : {len(ed_null_df):,}")
    print(f"  Unique patient IDs  : {ed_null_df['patient_id'].nunique():,}")

    print("\nED visits age window — signal (ch07_ed_visits_agewindow_signal.csv):")
    print(f"  Total rows          : {len(ed_signal_df):,}")
    print(f"  Unique patient IDs  : {ed_signal_df['patient_id'].nunique():,}")

    print("=" * 56)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    output_dir = pathlib.Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    print("Generating hospitalization claims...")
    hosp_df = make_hospitalization_data()

    print("Generating ED visit data...")
    ed_df = make_ed_visit_data()

    print("Generating nursing facility assessments...")
    nf_df = make_nursing_facility_data()

    print("Generating Medicaid coverage (2021-2022)...")
    cov_df = make_medicaid_coverage_data()

    print("Generating member demographics...")
    demog_df = make_member_demographics()

    print("Generating member demographics — correct DOB...")
    demog_correct_df = make_member_demographics_age18_21()

    print("Generating Medicaid coverage age window (2018-2025)...")
    age_cov_df = make_medicaid_coverage_age_window()

    print("Generating ED visits age window — null simulation...")
    ed_null_df = make_ed_visits_agewindow_null(demog_df)

    print("Generating ED visits age window — signal simulation...")
    ed_signal_df = make_ed_visits_agewindow_signal(demog_df)

    print_data_summary(
        hosp_df, ed_df, nf_df, cov_df, demog_df, demog_correct_df,
        age_cov_df, ed_null_df, ed_signal_df,
    )

    hosp_df.to_csv(      output_dir / "ch01_hospitalization_claims.csv",                  index=False)
    ed_df.to_csv(        output_dir / "ch01_06_ed_visits.csv",                     index=False)
    nf_df.to_csv(        output_dir / "ch02_03_nursing_facility_assessments.csv",            index=False)
    cov_df.to_csv(       output_dir / "ch04_06_medicaid_coverage.csv",             index=False)
    demog_df.to_csv(         output_dir / "ch04_07_member_demographics_mixed_dob.csv",               index=False)
    demog_correct_df.to_csv( output_dir / "ch04_07_member_demographics_age18_21.csv", index=False)
    age_cov_df.to_csv(   output_dir / "ch04_05_medicaid_coverage_agewindow.csv",   index=False)
    ed_df.to_csv(        output_dir / "ch06_ed_visits_agewindow.csv",              index=False)
    ed_null_df.to_csv(   output_dir / "ch07_ed_visits_agewindow_null.csv",      index=False)
    ed_signal_df.to_csv( output_dir / "ch07_ed_visits_agewindow_signal.csv",    index=False)
    for name in [
        "ch01_hospitalization_claims.csv",
        "ch01_06_ed_visits.csv",
        "ch02_03_nursing_facility_assessments.csv",
        "ch04_06_medicaid_coverage.csv",
        "ch04_07_member_demographics_mixed_dob.csv",
        "ch04_05_medicaid_coverage_agewindow.csv",
        "ch07_ed_visits_agewindow_null.csv",
        "ch07_ed_visits_agewindow_signal.csv",
        "ch04_07_member_demographics_age18_21.csv",
    ]:
        print(f"Saved: {output_dir / name}")
