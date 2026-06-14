# Reproducing the eventus Vignettes

This document provides step-by-step instructions for reproducing all
vignette results from the eventus manuscript.

All commands should be run from the **repo root** — the directory
containing this file.

---

## Requirements

Once published to PyPI:

```bash
pip install eventus
```

Until then, install from source:

```bash
git clone https://github.com/djarenas/eventus.git
cd eventus
pip install -e .
```

Python 3.10 or later is required.

---

## Step 1 — Generate the synthetic data

All vignettes use synthetic data generated from two scripts. Run both
once before running any chapter.

First, the core vignette data (Chapters 1–7):

```bash
python vignettes/data/generate_vignette_data.py
```

This creates the following files in `vignettes/data/`:

| File | Used in |
|---|---|
| `ch01_hospitalization_claims.csv` | Chapter 1 |
| `ch01_06_ed_visits.csv` | Chapter 1 (Bonus A), Chapter 6 |
| `ch02_03_nursing_facility_assessments.csv` | Chapters 2, 3 |
| `ch04_06_medicaid_coverage.csv` | Chapters 4, 6 |
| `ch04_05_medicaid_coverage_agewindow.csv` | Chapters 4 (Bonus A), 5 |
| `ch04_07_member_demographics_mixed_dob.csv` | Chapters 4, 7 |
| `ch04_07_member_demographics_age18_21.csv` | Chapters 4, 7 |
| `ch06_ed_visits_agewindow.csv` | Chapter 6 |
| `ch07_ed_visits_agewindow_null.csv` | Chapter 7 |
| `ch07_ed_visits_agewindow_signal.csv` | Chapter 7 |

Then, the co-occurrence data (Chapters 8–10):

```bash
python vignettes/data/generate_vignette_data_ch8x.py
```

This creates the following files in `vignettes/data/`:

| File | Used in |
|---|---|
| `ch08_11_simul1_cirrhosis_dx.csv` | Chapters 8, 9, 10 (simul_1) |
| `ch08_11_simul1_ed_visits.csv` | Chapters 8, 9, 10 (simul_1) |
| `ch08_09_simul2_event_x.csv` | Chapter 9 (simul_2) |
| `ch08_09_simul2_event_y.csv` | Chapter 9 (simul_2) |
| `ch08_09_simul3_event_x.csv` | Chapters 8, 9 (simul_3) |
| `ch08_09_simul3_event_y.csv` | Chapters 8, 9 (simul_3) |
| `ch09_10_simul4_mi_events.csv` | Chapters 9, 10 (simul_4) |
| `ch09_10_simul4_stroke_events.csv` | Chapters 9, 10 (simul_4) |
| `ch10_simul5_cardiovascular_events.csv` | Chapter 10 (simul_5) |
| `ch10_simul5_respiratory_infections.csv` | Chapter 10 (simul_5) |

For full simulation design rationale, parameters, and expected
statistical outcomes, see `vignettes/data/SIMULATION_DESIGN_CH01_07.md`
and `vignettes/data/SIMULATION_DESIGN_CH08-10.md`.

---

## Step 2 — Run the chapters

Each chapter is self-contained. Run any chapter independently after
generating the data:

```bash
# Chapter 1 — Cleaning hospitalization claims
python vignettes/chapter_01_cleaning/run_vignette_01.py

# Chapter 1 Bonus A — Cleaning ED visit events
python vignettes/chapter_01_cleaning/run_vignette_01_bonus_A.py

# Chapter 2 — Descriptor aggregation
python vignettes/chapter_02_descriptor_aggregation/run_vignette_02.py

# Chapter 3 — Stay duration analysis
python vignettes/chapter_03_duration/run_vignette_03.py

# Chapter 4 — Observation periods (calendar year)
python vignettes/chapter_04_observation_periods/run_vignette_04.py

# Chapter 4 Bonus A — Observation periods (age window)
python vignettes/chapter_04_observation_periods/run_vignette_04_bonus_A.py

# Chapter 5 — Stacked timeline visualization
python vignettes/chapter_05_stacked_timeline/run_vignette_05.py

# Chapter 6 — ED visit event volume
python vignettes/chapter_06_events/run_vignette_06.py

# Chapter 7 — Event timing and gap analysis
python vignettes/chapter_07_event_timing/run_vignette_07.py

# Chapter 8 — Event co-occurrence: presence
python vignettes/chapter_08_coevents/run_vignette_08.py

# Chapter 9 — Event co-occurrence: gap timing
python vignettes/chapter_09_gap_timing/run_vignette_09.py

# Chapter 10 — Event co-occurrence: directionality
python vignettes/chapter_10_directionality/run_vignette_10.py
```

Output figures are saved to each chapter's `output/` directory.

---

## Step 3 — Run all chapters at once (optional)

```bash
for script in \
    vignettes/chapter_01_cleaning/run_vignette_01.py \
    vignettes/chapter_01_cleaning/run_vignette_01_bonus_A.py \
    vignettes/chapter_02_descriptor_aggregation/run_vignette_02.py \
    vignettes/chapter_03_duration/run_vignette_03.py \
    vignettes/chapter_04_observation_periods/run_vignette_04.py \
    vignettes/chapter_04_observation_periods/run_vignette_04_bonus_A.py \
    vignettes/chapter_05_stacked_timeline/run_vignette_05.py \
    vignettes/chapter_06_events/run_vignette_06.py \
    vignettes/chapter_07_event_timing/run_vignette_07.py \
    vignettes/chapter_08_coevents/run_vignette_08.py \
    vignettes/chapter_09_gap_timing/run_vignette_09.py \
    vignettes/chapter_10_directionality/run_vignette_10.py; do
    echo "Running $script..."
    python "$script"
done
```

---

## Verifying the pinned results

The test suite re-runs the core vignette pipelines and asserts the exact
published numbers (cleaning counts, durations, co-occurrence statistics).
To verify your environment reproduces them:

```bash
pip install -e ".[dev]"
pytest
```

---

## Reproducibility guarantees

**All random seeds are fixed.** Every simulation in the data generators
uses an explicit `random_state` or `np.random.seed`. Running a generator
twice produces identical files.

**All visual decisions are versioned.** Every figure is driven by a
YAML config file in the chapter's `configs/` directory. The config file
is the complete record of every visual decision — bin widths, colors,
sample sizes, random seeds for sampling. Changing a config and rerunning
produces a different figure; the original config always reproduces the
original figure.

**All cleaning decisions are versioned.** Every cleaner is driven by a
YAML config file. The config file is the methods section — it declares
every cleaning decision made before any analysis begins.

**Sample selections are reproducible.** Chapter 5 uses
`ct.sample_subset(n=50, random_seed=42)`. The same seed always produces
the same 50 members.

---

## Without-eventus comparison scripts

Scripts implementing equivalent pipelines without the eventus framework
are provided for Chapters 1, 2, 4, 5, and 6:

```
vignettes/without_eventus/without_eventus_clean_hospitalizations.py
vignettes/without_eventus/without_eventus_clean_ed_visits.py
vignettes/without_eventus/without_eventus_clean_nursing_facility.py
vignettes/without_eventus/without_eventus_observation_periods.py
vignettes/without_eventus/without_eventus_stacked_timeline.py
vignettes/without_eventus/without_eventus_events.py
```

See `vignettes/without_eventus/without_eventus_README.md` for details.

Note: `without_eventus_observation_periods.py` raises an `AttributeError`
at runtime on the vignette dataset (`numpy.timedelta64` object has no
attribute `days`). This is documented in the Chapter 4 narrative and is
part of the comparison argument.

No without-eventus comparison scripts are provided for Chapters 7–10.
The comparison argument was made in full across Chapters 1–6. The
remaining chapters demonstrate analytical depth rather than the
cleaning/reproducibility argument.

---

## Questions

Please open a GitHub issue at
https://github.com/djarenas/eventus/issues.
