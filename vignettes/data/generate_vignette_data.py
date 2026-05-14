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
N_PATIENTS      = 500
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

    Parameters
    ----------
    seed : int
        Random seed for reproducibility. Default 42.

    Returns
    -------
    pd.DataFrame
        Columns: patient_id, ed_visit_date
    """
    rng = np.random.default_rng(seed + 1)   # different seed from hosp

    patient_ids = [f"P{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

    rows = []
    for pid in patient_ids:
        # Each patient has 0-8 ED visits across the full date range
        n_visits = int(rng.integers(0, 9))
        for _ in range(n_visits):
            visit_date = DATE_START + pd.Timedelta(
                days=int(rng.integers(0, (DATE_END - DATE_START).days))
            )
            rows.append({
                "patient_id":    pid,
                "ed_visit_date": visit_date,
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

    # ── Exact duplicates (~8%) ────────────────────────────────────────────────
    n_dupes  = int(len(df) * ED_DUPLICATE_RATE)
    dupe_idx = rng.choice(len(df), size=n_dupes, replace=True)
    dupes    = df.iloc[dupe_idx].copy()
    df       = pd.concat([df, dupes], ignore_index=True)

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


# ── Summary printer ───────────────────────────────────────────────────────────

def print_data_summary(hosp_df: pd.DataFrame, ed_df: pd.DataFrame) -> None:
    """Print a summary of the generated datasets."""
    print("=" * 56)
    print("Synthetic vignette data — summary")
    print("=" * 56)

    print("\nHospitalization claims:")
    print(f"  Total rows          : {len(hosp_df):,}")
    print(f"  Unique patient IDs  : {hosp_df['patient_id'].nunique():,}")
    print(f"  Null patient IDs    : {hosp_df['patient_id'].isna().sum():,}")
    print(f"  Null admit dates    : {hosp_df['admit_date'].isna().sum():,}")
    print(f"  Null icd10_condition: {hosp_df['icd10_condition'].isna().sum():,}")
    print(f"  Hospital_A rows     : {(hosp_df['hospital_id'] == 'Hospital_A').sum():,}")
    print(f"  Hospital_B rows     : {(hosp_df['hospital_id'] == 'Hospital_B').sum():,}")
    print(f"  Hospital_C rows     : {(hosp_df['hospital_id'] == 'Hospital_C').sum():,}")

    print("\nED visits:")
    print(f"  Total rows          : {len(ed_df):,}")
    print(f"  Unique patient IDs  : {ed_df['patient_id'].nunique():,}")
    print(f"  Null patient IDs    : {ed_df['patient_id'].isna().sum():,}")
    print(f"  Null visit dates    : {ed_df['ed_visit_date'].isna().sum():,}")
    print("=" * 56)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    output_dir = pathlib.Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    print("Generating hospitalization claims...")
    hosp_df = make_hospitalization_data()

    print("Generating ED visit data...")
    ed_df = make_ed_visit_data()

    print_data_summary(hosp_df, ed_df)

    hosp_path = output_dir / "hospitalization_claims.csv"
    ed_path   = output_dir / "ed_visits.csv"

    hosp_df.to_csv(hosp_path, index=False)
    ed_df.to_csv(ed_path,   index=False)

    print(f"\nSaved: {hosp_path}")
    print(f"Saved: {ed_path}")
