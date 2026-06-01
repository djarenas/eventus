"""
generate_vignette_data_ch8x.py
Synthetic data generator for eventus vignettes — Chapters 8–11.

Five simulation groups for demonstrating EventCoOccurrenceAnalyzer
across scientifically distinct co-occurrence scenarios.
All groups share the same 5,000-patient pool (D0001–D5000).

For full simulation design rationale, parameters, and expected
statistical outcomes see: vignettes/data/ch8-12_simulation_design.md

Usage
-----
    python vignettes/data/generate_vignette_data_ch8x.py

Output — all files saved to vignettes/data/
-------------------------------------------
simul_1 (cirrhosis_dx → ed_visit — presence + directed timing):
    ch08_11_simul1_cirrhosis_dx.csv       patient_id, diagnosis_date
    ch08_11_simul1_ed_visits.csv          patient_id, ed_visit_date

simul_2 (elevated prevalence via confounding, uniform timing):
    ch08_09_simul2_event_x.csv          patient_id, simul2_x_date
    ch08_09_simul2_event_y.csv          patient_id, simul2_y_date

simul_3 (pure null — no relationship):
    ch08_09_simul3_event_x.csv          patient_id, simul3_x_date
    ch08_09_simul3_event_y.csv          patient_id, simul3_y_date

simul_4 (MI ↔ stroke — clustered timing, random directionality):
    ch09_10_simul4_mi_events.csv          patient_id, mi_date
    ch09_10_simul4_stroke_events.csv      patient_id, stroke_date

simul_5 (respiratory_infection → cardiovascular_event — directed timing):
    ch10_simul5_respiratory_infections.csv  patient_id, resp_infection_date
    ch10_simul5_cardiovascular_events.csv   patient_id, cardiovascular_date
"""
from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd

# ── Shared constants ──────────────────────────────────────────────────────────

N_PATIENTS   = 5_000
ID_PREFIX    = "D"
DATE_START   = pd.Timestamp("2022-01-01")
DATE_END     = pd.Timestamp("2022-12-31")
TOTAL_DAYS   = (DATE_END - DATE_START).days   # 364

DUPLICATE_RATE = 0.05
NULL_DATE_RATE = 0.01

SEED_SIMUL1 = 42
SEED_SIMUL2 = 43
SEED_SIMUL3 = 44
SEED_SIMUL4 = 45
SEED_SIMUL5 = 46

PATIENT_IDS = [f"{ID_PREFIX}{str(i).zfill(4)}" for i in range(1, N_PATIENTS + 1)]

# ── simul_1 constants ─────────────────────────────────────────────────────────
# cirrhosis_diagnosis (one-time) → ed_visit (recurring)
# Elevated presence + directed temporal clustering A→B

S1_CIRRHOSIS_PREV       = 0.02   # 2% cirrhosis prevalence (general Medicaid population)
S1_ED_RATE_CIRRHOSIS    = 2.0    # Poisson lambda/year — cirrhosis patients
S1_ED_RATE_NO_CIRRHOSIS = 0.4    # Poisson lambda/year — non-cirrhosis
S1_ED_RATE_NOISE        = 1.2    # Poisson lambda/year — 10% high utilizers
S1_NOISE_FRAC           = 0.10
S1_CLUSTER_MEAN_DAYS    = 45     # Exponential mean for post-diagnosis clustering
S1_CLUSTER_CAP_DAYS     = 90     # Clustered visits within 90 days of dx

# ── simul_2 constants ─────────────────────────────────────────────────────────
# Elevated prevalence via confounding, uniform timing — no temporal signal
# Both events elevated in same high-utilizer patients, independently

S2_UTIL_PREV       = 0.20   # 20% high utilizers
S2_RATE_HIGH_UTIL  = 3.0    # Poisson lambda/year — both events elevated
S2_RATE_REGULAR    = 0.3    # Poisson lambda/year — regular patients

# ── simul_3 constants ─────────────────────────────────────────────────────────
# Pure null — no relationship in prevalence, timing, or directionality

S3_RATE = 0.3    # Same Poisson lambda/year for everyone, both events

# ── simul_4 constants ─────────────────────────────────────────────────────────
# MI ↔ stroke — elevated prevalence + clustered timing + random directionality
# Both events recur. Shared cardiovascular risk group drives co-occurrence.
# When MI occurs, stroke drawn from symmetric ±60-day window (and vice versa).
# Based on published estimates: ~10% of patients have elevated CV risk,
# post-MI stroke risk and post-stroke MI risk both elevated within 90 days.

S4_CV_RISK_PREV    = 0.10   # 10% have elevated cardiovascular risk
S4_MI_RATE_HIGH    = 1.5    # Poisson lambda/year — high CV risk
S4_STROKE_RATE_HIGH = 1.5   # Poisson lambda/year — high CV risk (symmetric)
S4_MI_RATE_LOW     = 0.05   # Poisson lambda/year — general population
S4_STROKE_RATE_LOW = 0.04   # Poisson lambda/year — general population
S4_WINDOW_DAYS     = 60     # Symmetric ±60-day window for clustering

# ── simul_5 constants ─────────────────────────────────────────────────────────
# respiratory_infection → cardiovascular_event — directed temporal clustering
# Respiratory infections trigger cardiovascular events within ~30 days.
# Based on published literature (Kwong et al. 2018 — influenza and MI risk).

S5_RESP_RATE       = 1.5    # Poisson lambda/year — respiratory infections (all)
S5_CV_TRIGGER_PROB = 0.08   # 8% of resp infections trigger a CV event
S5_CV_TRIGGER_DAYS = 30     # Exponential mean: CV event within ~30 days of resp
S5_CV_BACKGROUND   = 0.10   # Poisson lambda/year — background CV events (all)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _uniform_date(rng: np.random.Generator, n: int) -> list[pd.Timestamp]:
    """Draw n dates uniformly from the observation period."""
    if n == 0:
        return []
    days = rng.integers(0, TOTAL_DAYS, size=n)
    return [DATE_START + pd.Timedelta(days=int(d)) for d in days]


def _fmt_date(ts) -> str | None:
    """Format a Timestamp as YYYY-MM-DD string, or None if NaT."""
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _add_noise(
    df:       pd.DataFrame,
    date_col: str,
    rng:      np.random.Generator,
) -> pd.DataFrame:
    """Add duplicate rows (~5%) and null dates (~1%) to a DataFrame."""
    df = df.copy()
    n_dupes = max(0, int(len(df) * DUPLICATE_RATE))
    if n_dupes > 0:
        idx  = rng.choice(len(df), size=n_dupes, replace=True)
        df   = pd.concat([df, df.iloc[idx]], ignore_index=True)
    n_nulls  = max(1, int(len(df) * NULL_DATE_RATE))
    null_idx = rng.choice(len(df), size=n_nulls, replace=False)
    df.loc[null_idx, date_col] = None
    return df.sample(
        frac=1, random_state=int(rng.integers(0, 9999))
    ).reset_index(drop=True)


# ── simul_1 generator ─────────────────────────────────────────────────────────

def make_simul1(seed: int = SEED_SIMUL1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate cirrhosis diagnosis events (one-time) and ED visits (recurring).

    Cirrhosis patients (~7%) have elevated ED visit rates and their
    visits cluster within 90 days of diagnosis (Exponential mean=45 days).
    Diagnosis always precedes clustered ED visits — directed A→B signal.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (cirrhosis_df, ed_df)
        cirrhosis_df : patient_id, diagnosis_date  (at most one row per patient)
        ed_df        : patient_id, ed_visit_date
    """
    rng = np.random.default_rng(seed)

    cirrh_rows = []
    ed_rows    = []

    for pid in PATIENT_IDS:
        has_cirrhosis = rng.random() < S1_CIRRHOSIS_PREV

        if has_cirrhosis:
            dx_day  = int(rng.integers(0, TOTAL_DAYS))
            dx_date = DATE_START + pd.Timedelta(days=dx_day)
            cirrh_rows.append({
                "patient_id":     pid,
                "diagnosis_date": _fmt_date(dx_date),
            })
            # Clustered ED visits post-diagnosis
            n_clustered = int(rng.poisson(
                S1_ED_RATE_CIRRHOSIS * S1_CLUSTER_CAP_DAYS / 365
            ))
            for _ in range(n_clustered):
                gap = rng.exponential(S1_CLUSTER_MEAN_DAYS)
                if gap <= S1_CLUSTER_CAP_DAYS:
                    visit_date = dx_date + pd.Timedelta(days=int(gap))
                    if DATE_START <= visit_date <= DATE_END:
                        ed_rows.append({
                            "patient_id":    pid,
                            "ed_visit_date": _fmt_date(visit_date),
                        })
            # Background ED visits
            for visit_date in _uniform_date(rng, int(rng.poisson(
                S1_ED_RATE_CIRRHOSIS * 0.3
            ))):
                ed_rows.append({
                    "patient_id":    pid,
                    "ed_visit_date": _fmt_date(visit_date),
                })
        else:
            is_noise = rng.random() < S1_NOISE_FRAC
            rate     = S1_ED_RATE_NOISE if is_noise else S1_ED_RATE_NO_CIRRHOSIS
            for visit_date in _uniform_date(rng, int(rng.poisson(rate))):
                ed_rows.append({
                    "patient_id":    pid,
                    "ed_visit_date": _fmt_date(visit_date),
                })

    cirrh_df = pd.DataFrame(cirrh_rows) if cirrh_rows else pd.DataFrame(
        columns=["patient_id", "diagnosis_date"]
    )
    ed_df = pd.DataFrame(ed_rows) if ed_rows else pd.DataFrame(
        columns=["patient_id", "ed_visit_date"]
    )

    # Cirrhosis: null dates only — no duplicate rows since a patient
    # can have at most one cirrhosis diagnosis
    if len(cirrh_df) > 0:
        n_nulls  = max(1, int(len(cirrh_df) * NULL_DATE_RATE))
        null_idx = rng.choice(len(cirrh_df), size=n_nulls, replace=False)
        cirrh_df = cirrh_df.copy()
        cirrh_df.loc[null_idx, "diagnosis_date"] = None
    ed_df = _add_noise(ed_df, "ed_visit_date", rng)
    return cirrh_df, ed_df


# ── simul_2 generator ─────────────────────────────────────────────────────────

def make_simul2(seed: int = SEED_SIMUL2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate two event streams with elevated co-occurrence via confounding
    but no temporal relationship — uniform timing.

    High-utilizer patients (~20%) independently generate both event streams
    at elevated rates. Events are uniformly distributed — no mechanism links
    an X event to a Y event. Co-occurrence is purely from shared utilization.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (event_x_df, event_y_df)
        event_x_df : patient_id, simul2_x_date
        event_y_df : patient_id, simul2_y_date
    """
    rng = np.random.default_rng(seed)

    x_rows = []
    y_rows = []

    for pid in PATIENT_IDS:
        is_util = rng.random() < S2_UTIL_PREV
        rate    = S2_RATE_HIGH_UTIL if is_util else S2_RATE_REGULAR

        for x_date in _uniform_date(rng, int(rng.poisson(rate))):
            x_rows.append({"patient_id": pid, "simul2_x_date": _fmt_date(x_date)})
        for y_date in _uniform_date(rng, int(rng.poisson(rate))):
            y_rows.append({"patient_id": pid, "simul2_y_date": _fmt_date(y_date)})

    x_df = pd.DataFrame(x_rows) if x_rows else pd.DataFrame(
        columns=["patient_id", "simul2_x_date"]
    )
    y_df = pd.DataFrame(y_rows) if y_rows else pd.DataFrame(
        columns=["patient_id", "simul2_y_date"]
    )

    x_df = _add_noise(x_df, "simul2_x_date", rng)
    y_df = _add_noise(y_df, "simul2_y_date", rng)
    return x_df, y_df


# ── simul_3 generator ─────────────────────────────────────────────────────────

def make_simul3(seed: int = SEED_SIMUL3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate two completely independent event streams — pure null.

    No relationship in prevalence, timing, or directionality.
    All three statistical tests should return non-significant results.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (event_x_df, event_y_df)
        event_x_df : patient_id, simul3_x_date
        event_y_df : patient_id, simul3_y_date
    """
    rng = np.random.default_rng(seed)

    x_rows = []
    y_rows = []

    for pid in PATIENT_IDS:
        for x_date in _uniform_date(rng, int(rng.poisson(S3_RATE))):
            x_rows.append({"patient_id": pid, "simul3_x_date": _fmt_date(x_date)})
        for y_date in _uniform_date(rng, int(rng.poisson(S3_RATE))):
            y_rows.append({"patient_id": pid, "simul3_y_date": _fmt_date(y_date)})

    x_df = pd.DataFrame(x_rows) if x_rows else pd.DataFrame(
        columns=["patient_id", "simul3_x_date"]
    )
    y_df = pd.DataFrame(y_rows) if y_rows else pd.DataFrame(
        columns=["patient_id", "simul3_y_date"]
    )

    x_df = _add_noise(x_df, "simul3_x_date", rng)
    y_df = _add_noise(y_df, "simul3_y_date", rng)
    return x_df, y_df


# ── simul_4 generator ─────────────────────────────────────────────────────────

def make_simul4(seed: int = SEED_SIMUL4) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate MI and stroke events — elevated prevalence + clustered timing
    + random directionality.

    Patients with elevated cardiovascular risk (~10%) have both elevated MI
    and stroke rates. When an MI occurs, a stroke is drawn from a symmetric
    ±60-day window (and vice versa) — temporal clustering without consistent
    ordering. Based on published estimates of post-MI stroke risk and
    post-stroke MI risk (both elevated within 90 days).

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (mi_df, stroke_df)
        mi_df     : patient_id, mi_date
        stroke_df : patient_id, stroke_date
    """
    rng = np.random.default_rng(seed)

    mi_rows     = []
    stroke_rows = []

    for pid in PATIENT_IDS:
        is_high_cv = rng.random() < S4_CV_RISK_PREV

        if is_high_cv:
            mi_rate     = S4_MI_RATE_HIGH
            stroke_rate = S4_STROKE_RATE_HIGH
        else:
            mi_rate     = S4_MI_RATE_LOW
            stroke_rate = S4_STROKE_RATE_LOW

        # Generate MI events
        mi_dates = _uniform_date(rng, int(rng.poisson(mi_rate)))
        for mi_date in mi_dates:
            mi_rows.append({"patient_id": pid, "mi_date": _fmt_date(mi_date)})
            # Each MI triggers a stroke in symmetric ±60-day window
            if is_high_cv:
                offset     = int(rng.integers(-S4_WINDOW_DAYS, S4_WINDOW_DAYS + 1))
                stroke_date = mi_date + pd.Timedelta(days=offset)
                if DATE_START <= stroke_date <= DATE_END:
                    stroke_rows.append({
                        "patient_id":  pid,
                        "stroke_date": _fmt_date(stroke_date),
                    })

        # Generate independent stroke events
        for stroke_date in _uniform_date(rng, int(rng.poisson(stroke_rate * 0.3))):
            stroke_rows.append({"patient_id": pid, "stroke_date": _fmt_date(stroke_date)})

    mi_df = pd.DataFrame(mi_rows) if mi_rows else pd.DataFrame(
        columns=["patient_id", "mi_date"]
    )
    stroke_df = pd.DataFrame(stroke_rows) if stroke_rows else pd.DataFrame(
        columns=["patient_id", "stroke_date"]
    )

    mi_df     = _add_noise(mi_df,     "mi_date",     rng)
    stroke_df = _add_noise(stroke_df, "stroke_date", rng)
    return mi_df, stroke_df


# ── simul_5 generator ─────────────────────────────────────────────────────────

def make_simul5(seed: int = SEED_SIMUL5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate respiratory infection and cardiovascular events —
    elevated prevalence + clustered timing + directed A→B.

    Respiratory infections occur at λ=1.5/year for all patients.
    Each respiratory infection has an 8% probability of triggering a
    cardiovascular event within ~30 days (Exponential mean=15 days).
    Background cardiovascular events occur independently at λ=0.1/year.

    Based on published literature: Kwong et al. (2018) found a 6-fold
    increase in MI risk in the week following influenza diagnosis.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (resp_df, cv_df)
        resp_df : patient_id, resp_infection_date
        cv_df   : patient_id, cardiovascular_date
    """
    rng = np.random.default_rng(seed)

    resp_rows = []
    cv_rows   = []

    for pid in PATIENT_IDS:
        # Respiratory infections — all patients
        resp_dates = _uniform_date(rng, int(rng.poisson(S5_RESP_RATE)))

        for resp_date in resp_dates:
            resp_rows.append({
                "patient_id":        pid,
                "resp_infection_date": _fmt_date(resp_date),
            })
            # Each resp infection has S5_CV_TRIGGER_PROB chance of
            # triggering a CV event within ~30 days — directed A→B
            if rng.random() < S5_CV_TRIGGER_PROB:
                gap     = rng.exponential(15)   # mean 15 days
                cv_date = resp_date + pd.Timedelta(days=int(gap))
                if cv_date <= DATE_END:
                    cv_rows.append({
                        "patient_id":         pid,
                        "cardiovascular_date": _fmt_date(cv_date),
                    })

        # Background CV events — independent of respiratory infections
        for cv_date in _uniform_date(rng, int(rng.poisson(S5_CV_BACKGROUND))):
            cv_rows.append({
                "patient_id":         pid,
                "cardiovascular_date": _fmt_date(cv_date),
            })

    resp_df = pd.DataFrame(resp_rows) if resp_rows else pd.DataFrame(
        columns=["patient_id", "resp_infection_date"]
    )
    cv_df = pd.DataFrame(cv_rows) if cv_rows else pd.DataFrame(
        columns=["patient_id", "cardiovascular_date"]
    )

    resp_df = _add_noise(resp_df, "resp_infection_date", rng)
    cv_df   = _add_noise(cv_df,   "cardiovascular_date", rng)
    return resp_df, cv_df


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(
    s1_cirrh_df, s1_ed_df,
    s2_x_df, s2_y_df,
    s3_x_df, s3_y_df,
    s4_mi_df, s4_stroke_df,
    s5_resp_df, s5_cv_df,
) -> None:
    print("=" * 60)
    print("Synthetic vignette data ch8x — summary")
    print(f"Patient pool : D0001–D{str(N_PATIENTS).zfill(4)}  ({N_PATIENTS:,} patients)")
    print(f"Obs period   : {DATE_START.date()} → {DATE_END.date()}")
    print("=" * 60)

    def _row(label, df, date_col):
        n_rows     = len(df)
        n_entities = df["patient_id"].nunique()
        n_null     = df[date_col].isna().sum() if date_col in df else 0
        print(f"  {label:<45} rows={n_rows:>6,}  entities={n_entities:>5,}  nulls={n_null:>4,}")

    print("\nsimul_1 — cirrhosis_dx (one-time) → ed_visit (directed)")
    _row("ch08_11_simul1_cirrhosis_dx.csv",              s1_cirrh_df, "diagnosis_date")
    _row("ch08_11_simul1_ed_visits.csv",                 s1_ed_df,    "ed_visit_date")

    print("\nsimul_2 — confounding, uniform timing (presence only)")
    _row("simul2_event_x.csv",                 s2_x_df,     "simul2_x_date")
    _row("simul2_event_y.csv",                 s2_y_df,     "simul2_y_date")

    print("\nsimul_3 — pure null")
    _row("simul3_event_x.csv",                 s3_x_df,     "simul3_x_date")
    _row("simul3_event_y.csv",                 s3_y_df,     "simul3_y_date")

    print("\nsimul_4 — MI ↔ stroke (clustered, undirected)")
    _row("ch09_10_simul4_mi_events.csv",                      s4_mi_df,    "mi_date")
    _row("ch09_10_simul4_stroke_events.csv",                  s4_stroke_df,"stroke_date")

    print("\nsimul_5 — respiratory_infection → cardiovascular (directed)")
    _row("ch10_simul5_respiratory_infections.csv",         s5_resp_df,  "resp_infection_date")
    _row("ch10_simul5_cardiovascular_events.csv",          s5_cv_df,    "cardiovascular_date")

    print("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    output_dir = pathlib.Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    print("Generating simul_1 — cirrhosis_dx → ed_visit...")
    s1_cirrh_df, s1_ed_df = make_simul1()

    print("Generating simul_2 — confounding, uniform timing...")
    s2_x_df, s2_y_df = make_simul2()

    print("Generating simul_3 — pure null...")
    s3_x_df, s3_y_df = make_simul3()

    print("Generating simul_4 — MI ↔ stroke...")
    s4_mi_df, s4_stroke_df = make_simul4()

    print("Generating simul_5 — respiratory_infection → cardiovascular...")
    s5_resp_df, s5_cv_df = make_simul5()

    print_summary(
        s1_cirrh_df, s1_ed_df,
        s2_x_df, s2_y_df,
        s3_x_df, s3_y_df,
        s4_mi_df, s4_stroke_df,
        s5_resp_df, s5_cv_df,
    )

    # Save all files
    s1_cirrh_df.to_csv( output_dir / "ch08_11_simul1_cirrhosis_dx.csv",        index=False)
    s1_ed_df.to_csv(    output_dir / "ch08_11_simul1_ed_visits.csv",            index=False)
    s2_x_df.to_csv(     output_dir / "ch08_09_simul2_event_x.csv",            index=False)
    s2_y_df.to_csv(     output_dir / "ch08_09_simul2_event_y.csv",            index=False)
    s3_x_df.to_csv(     output_dir / "ch08_09_simul3_event_x.csv",            index=False)
    s3_y_df.to_csv(     output_dir / "ch08_09_simul3_event_y.csv",            index=False)
    s4_mi_df.to_csv(    output_dir / "ch09_10_simul4_mi_events.csv",                 index=False)
    s4_stroke_df.to_csv(output_dir / "ch09_10_simul4_stroke_events.csv",             index=False)
    s5_resp_df.to_csv(  output_dir / "ch10_simul5_respiratory_infections.csv",    index=False)
    s5_cv_df.to_csv(    output_dir / "ch10_simul5_cardiovascular_events.csv",     index=False)

    print(f"\nAll files saved to: {output_dir.resolve()}")

    expected = [
        "ch08_11_simul1_cirrhosis_dx.csv",
        "ch08_11_simul1_ed_visits.csv",
        "ch08_09_simul2_event_x.csv",
        "ch08_09_simul2_event_y.csv",
        "ch08_09_simul3_event_x.csv",
        "ch08_09_simul3_event_y.csv",
        "ch09_10_simul4_mi_events.csv",
        "ch09_10_simul4_stroke_events.csv",
        "ch10_simul5_respiratory_infections.csv",
        "ch10_simul5_cardiovascular_events.csv",
    ]
    for fname in expected:
        path   = output_dir / fname
        status = "✓" if path.exists() else "✗ MISSING"
        print(f"  {status}  {fname}")
