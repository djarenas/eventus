# Reproducing the eventus Vignettes

This document provides step-by-step instructions for reproducing all
vignette results from the eventus JSS submission.

All commands should be run from the **repo root** — the directory
containing this file.

---

## Requirements

```bash
pip install eventus
```

Or install from source:

```bash
git clone https://github.com/your-org/eventus.git
cd eventus
pip install -e .
```

Python 3.9 or later is required.

---

## Step 1 — Generate the synthetic data

All vignettes use synthetic data generated from a single script.
Run this once before running any chapter:

```bash
python vignettes/data/generate_vignette_data.py
```

This creates the following files in `vignettes/data/`:

| File | Used in |
|---|---|
| `hospitalization_claims.csv` | Chapter 1 |
| `simulated_ed_visits.csv` | Chapters 1 (Bonus A), 6 |
| `nursing_facility_assessments.csv` | Chapters 2, 3 |
| `simulated_medicaid_coverage.csv` | Chapters 4, 6 |
| `simulated_member_demographics.csv` | Chapters 4 (Bonus A), 5, 6 (Bonus B), 7 |
| `simulated_medicaid_coverage_agewindow.csv` | Chapters 4 (Bonus A), 5 |
| `simulated_ed_visits_agewindow_null.csv` | Chapter 7 |
| `simulated_ed_visits_agewindow_signal.csv` | Chapter 7 |

Then run the co-occurrence data generator (Chapters 8–12):

```bash
python vignettes/data/generate_vignette_data_ch8x.py
```

This creates the following files in `vignettes/data/`:

| File | Used in |
|---|---|
| `simulated_cirrhosis_dx_ch08.csv` | Chapters 8–12 (simul_1) |
| `simulated_ed_visits_ch08.csv` | Chapters 8–12 (simul_1) |
| `simulated_simul2_event_x.csv` | Chapters 9, 10, 11 (simul_2) |
| `simulated_simul2_event_y.csv` | Chapters 9, 10, 11 (simul_2) |
| `simulated_simul3_event_x.csv` | Chapters 8, 11 (simul_3) |
| `simulated_simul3_event_y.csv` | Chapters 8, 11 (simul_3) |
| `simulated_simul4_event_x.csv` | Chapters 8, 11, 12 (simul_4) |
| `simulated_simul4_event_y.csv` | Chapters 8, 11, 12 (simul_4) |

For full simulation design rationale, parameters, and expected
statistical outcomes, see `ch8-12_simulation_design.md`.

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
python vignettes/chapter_03_stay_duration/run_vignette_03.py

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

# Chapter 8 — Event co-occurrence analysis (presence + gaps)
python vignettes/chapter_08_coevent/run_vignette_08.py

# Chapters 9–12 — pending implementation
# python vignettes/chapter_09_gap_timing/run_vignette_09.py
# python vignettes/chapter_10_directionality/run_vignette_10.py
# python vignettes/chapter_11_statistical_tests/run_vignette_11.py
# python vignettes/chapter_12_survival/run_vignette_12.py
```

Output figures are saved to each chapter's `output/` directory.

---

## Step 3 — Run all chapters at once (optional)

```bash
for script in \
    vignettes/chapter_01_cleaning/run_vignette_01.py \
    vignettes/chapter_01_cleaning/run_vignette_01_bonus_A.py \
    vignettes/chapter_02_descriptor_aggregation/run_vignette_02.py \
    vignettes/chapter_03_stay_duration/run_vignette_03.py \
    vignettes/chapter_04_observation_periods/run_vignette_04.py \
    vignettes/chapter_04_observation_periods/run_vignette_04_bonus_A.py \
    vignettes/chapter_05_stacked_timeline/run_vignette_05.py \
    vignettes/chapter_06_events/run_vignette_06.py \
    vignettes/chapter_07_event_timing/run_vignette_07.py \
    vignettes/chapter_08_coevent/run_vignette_08.py; do
    echo "Running $script..."
    python "$script"
done
```

---

## Reproducibility guarantees

**All random seeds are fixed.** Every simulation in
`generate_vignette_data.py` uses an explicit `random_state` or
`np.random.seed`. Running the data generator twice produces identical
files.

**All visual decisions are versioned.** Every figure is driven by a
YAML config file in the chapter's `configs/` directory. The config
file is the complete record of every visual decision — bin widths,
colors, sample sizes, random seeds for sampling. Changing a config
and rerunning produces a different figure; the original config always
reproduces the original figure.

**All cleaning decisions are versioned.** Every cleaner is driven by
a YAML config file. The config file is the methods section — it
declares every cleaning decision made before any analysis begins.

**Sample selections are reproducible.** Chapter 5 uses
`ct.sample_subset(n=50, random_seed=42)`. The same seed always
produces the same 50 members.

---

## Without-eventus comparison scripts

Scripts implementing equivalent pipelines without the eventus
framework are provided for Chapters 1, 2, 4, 5, and 6:

```
vignettes/without_eventus/without_eventus_clean_hospitalizations.py
vignettes/without_eventus/without_eventus_clean_nursing_facility.py
vignettes/without_eventus/without_eventus_observation_periods.py
vignettes/without_eventus/without_eventus_stacked_timeline.py
vignettes/without_eventus/without_eventus_events.py
```

Note: `without_eventus_observation_periods.py` raises an
`AttributeError` at runtime on the vignette dataset
(`numpy.timedelta64` object has no attribute `days`). This is
documented in the Chapter 4 narrative and is part of the comparison
argument.

No without-eventus comparison scripts are provided for Chapters 7–12.
The comparison argument was made in full across Chapters 1–6. The
remaining chapters demonstrate analytical depth rather than the
cleaning/reproducibility argument.

---

## Questions

Please open a GitHub issue or contact the corresponding author.
