# Chapter 8 — Event Co-occurrence: Presence Analysis

## Vignette: Do Cirrhosis Diagnoses and ED Visits Co-occur Above Chance?

You have two cleaned event streams for a cohort of 5,000 patients:
cirrhosis diagnosis dates and emergency department visits. Both cover
calendar year 2022. Both were cleaned independently — separate
semantics, separate cleaner configs, separate audit reports.

The scientific question is: *"Among patients with a cirrhosis
diagnosis, what proportion also had an ED visit — and is that
proportion meaningfully higher than among patients without a cirrhosis
diagnosis?"*

This is a presence question. It asks whether two events tend to
co-occur in the same observation period more than chance would
predict. It makes no claim about timing, ordering, or the mechanism
behind the association. Those questions come later.

> *This chapter uses synthetic data designed for the co-occurrence
> vignette series. See `ch8-12_simulation_design.md` for full
> simulation parameters and rationale.*

---

### The five problems

**Problem 1 — Co-occurrence counting requires a per-entity merge
across two differently-shaped tables.** A script has two separate
DataFrames — one for cirrhosis diagnoses, one for ED visits. Computing
co-occurrence requires merging them by patient ID, handling patients
who appear in one but not the other, and carefully accounting for
patients with neither event. Each step is a place where a bug silently
produces wrong counts. A left join that drops non-matching rows gives
a different answer than an outer join. A groupby that forgets to
include the full patient list undercounts the "neither" cell. A script
that gets any one of these wrong produces plausible-looking but
incorrect results with no indication that anything failed.

**Problem 2 — The denominator must be declared for the full cohort.**
*"Among cirrhosis patients, 87% also had an ED visit"* — compelling,
but only meaningful if the denominator is right. The comparison group
must be patients without a cirrhosis diagnosis from the same
population, not just patients who appeared in one of the event
DataFrames. A script that builds its patient list from the union of
two event DataFrames silently excludes patients with neither event —
corrupting both the prevalence estimates and the 2×2 table.

**Problem 3 — The column-naming problem is worst here.** A script
computing co-occurrence statistics produces a dictionary or a
DataFrame with column names invented on the spot: `n_cirrh_and_ed`,
`count_both`, `pct_co`. None of these are self-describing.
`EventCoOccurrencePresenceResult` carries `n_with_a`, `n_with_b`,
`n_with_both`, `n_with_neither`, `p_b_given_a`, `p_b_given_no_a` as
named, documented properties of a validated object. The column-naming
problem disappears when results carry their own context.

**Problem 4 — Building the 2×2 table correctly requires the full
cohort.** The four cells of a co-occurrence contingency table — both,
A only, B only, neither — each need the right denominator. The
"neither" cell — patients who had neither event within the observation
period — cannot be computed from the two event DataFrames alone. It
requires the full patient list. `EventCoOccurrenceAnalyzer` receives
the `CohortTimeline` directly. The full cohort is already there.

**Problem 5 — The observation period must cover the full cohort, not
just patients who had events.** Patients with neither event must be
present in the `CohortTimeline` for the 2×2 table to be correct.
Deriving the patient list from the event DataFrames silently drops
them and produces wrong association measures — a silent correctness
error that produces plausible-looking but meaningless results.

---

## The eventus solution

### Step 1 — Clean both streams independently

Each stream gets its own semantics, its own cleaner config, its own
audit report. Neither knows about the other.

```python
import eventus
import pandas as pd

cirrh_raw_df = pd.read_csv("data/ch08_11_simul1_cirrhosis_dx.csv")
ed_raw_df    = pd.read_csv("data/ch08_11_simul1_ed_visits.csv")

# Cirrhosis diagnoses
cirrh_sem     = eventus.EventSemantics.build_from_yaml("configs/cirrhosis_ch08_semantics.yaml")
cirrh_config  = eventus.EventsCleanerConfig.build_from_yaml("configs/cirrhosis_ch08_cleaner.yaml")
cirrh_cleaner = eventus.EventsCleaner(cirrh_raw_df, cirrh_sem, cirrh_config)
cirrhosis     = cirrh_cleaner.clean()
cirrh_cleaner.print_report()

# ED visits
ed_sem     = eventus.EventSemantics.build_from_yaml("configs/ed_ch08_semantics.yaml")
ed_config  = eventus.EventsCleanerConfig.build_from_yaml("configs/ed_ch08_cleaner.yaml")
ed_cleaner = eventus.EventsCleaner(ed_raw_df, ed_sem, ed_config)
ed_visits  = ed_cleaner.clean()
ed_cleaner.print_report()
```

```
Cleaning report — cirrhosis diagnoses
────────────────────────────────────────────────────────
Total input rows:                               345
  Rejected:
    duplicate_row:                               16   (4.6%)
    null_date:                                    3   (0.9%)
────────────────────────────────────────────────────────
Clean rows:                                     326   (94.5%)

Cleaning report — ED visits
────────────────────────────────────────────────────────
Total input rows:                             2,678
  Rejected:
    duplicate_row:                              126   (4.7%)
    null_date:                                   26   (1.0%)
────────────────────────────────────────────────────────
Clean rows:                                   2,526   (94.3%)
```

Two separate reports. Two separate audit trails. Nothing silent.

### Step 2 — Declare the full cohort observation period

The observation period is constructed from the full 5,000-patient
pool — explicitly declared, not derived from either event stream.

```python
# Full patient pool — declared explicitly, not inferred from events
all_ids = [f"D{str(i).zfill(4)}" for i in range(1, 5001)]

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)
```

This is the answer to Problem 5. Patients with neither event are
present in the `CohortTimeline` from the start. They correctly
populate the "neither" cell of the 2×2 table.

### Step 3 — Assemble the CohortTimeline

```python
cirrhosis = eventus.EventsFilter(cirrhosis).to_obs_period(obs).result
ed_visits = eventus.EventsFilter(ed_visits).to_obs_period(obs).result

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    events     = [cirrhosis, ed_visits],
)

print(ct)
```

```
CohortTimeline(
  entities         : 5,000
  has_obs_period   : True
  event_identities : ['cirrhosis_diagnosis', 'ed_visit']
)
```

All 5,000 patients present — including the 2,980 (59.6%) with
neither event. They are the "neither" cell.

Both streams assembled. One row per patient. 5,000 rows — every
patient accounted for, whether they had zero events or many.

### Step 4 — Compute presence

```python
analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "cirrhosis_diagnosis",
    identity_b      = "ed_visit",
)

presence = analyzer.compute_presence()
print(presence)
```

```
EventCoOccurrencePresenceResult:
  identity_a        : cirrhosis_diagnosis
  identity_b        : ed_visit
  entities          : 5,000
  ────────────────────────────────────────────
  n_with_a          : 90 (1.8%)       ← cirrhosis patients
  n_with_b          : 1,847 (36.9%)  ← any ED visit
  n_with_both       : 56    (1.1%)    ← both
  n_with_neither    : 3,119 (62.4%)   ← neither
  ────────────────────────────────────────────
  p_b_given_a       : 62.2%           ← P(ED visit | cirrhosis)
  p_b_given_no_a    : 36.5%           ← P(ED visit | no cirrhosis)
  prevalence_ratio  : 1.706×
  ────────────────────────────────────────────
  fisher_exact_p    : 1.27e-06
```

`p_b_given_a` is the core of the chapter 08 story: among patients
with a cirrhosis diagnosis, what proportion also had an ED visit?
`p_b_given_no_a` is the comparison: the same proportion among
patients without a diagnosis. The prevalence ratio is their ratio.
The Fisher's exact p-value tests whether the difference is above
what chance would produce.

### Step 5 — The association object

```python
assoc = presence.association
print(assoc)
```

```
EventCoOccurrenceAssociation:
  identity_a : cirrhosis_diagnosis
  identity_b : ed_visit
  n_total    : 5,000

  Contingency table:
                           has_ed_visit      no_ed_visit           total
  has_cirrhosis_diagnosis    56 (1.1%)        34 (0.7%)     90 (1.8%)
  no_cirrhosis_diagnosis  1,791 (35.8%)  3,119 (62.4%)  4,910 (98.2%)
  total                   1,847 (36.9%)  3,153 (63.1%)  5,000 (100.0%)

  P(ed_visit | cirrhosis_diagnosis)           : 62.2%  (95% CI: 51.9% – 71.5%)
  P(ed_visit | no cirrhosis_diagnosis)    : 36.5%  (95% CI: 35.1% – 37.8%)
  P(cirrhosis_diagnosis | ed_visit)       : 3.0%   (95% CI: 2.3% – 3.9%)
  P(cirrhosis_diagnosis | no ed_visit)    : 1.1%   (95% CI: 0.8% – 1.5%)
  prevalence_ratio                        : 1.706  (95% CI: 1.446 – 2.012)

  disclaimer: Observational association within a defined observation
              period. Describes co-occurrence patterns — not mechanisms,
              not directionality, not clinical relationships.
```

`presence.association` returns a full association analysis derived
from the 2×2 table — conditional probabilities with Wilson CIs,
prevalence ratio with log-method CI, and a disclaimer. No additional
data is needed beyond what `compute_presence()` already computed.

Among cirrhosis patients, 62.2% also had an ED visit in 2022 —
nearly double the 36.5% rate among non-cirrhosis patients. The
prevalence ratio of 1.71 (95% CI: 1.45–2.01) is highly significant
(Fisher p=1.27e-06). With only 90 cirrhosis patients (1.8% prevalence)
the CI is wider than at higher prevalence, but the signal is clear.
This is consistent with the simulation design: cirrhosis patients were
assigned an ED visit rate of λ=2.0/year vs λ=0.4/year for non-cirrhosis.

The disclaimer is part of the object because it is always true for
observational co-occurrence statistics. A presence result describes
co-occurrence patterns — not mechanisms, not directionality, not
clinical relationships. Those questions are for later chapters.

---

## Validation — the null case

To confirm the analyzer correctly identifies absence of signal, we run
the same pipeline on simul_3 — two independent event streams with uniform rates
with identical rates for all 5,000 patients. No relationship in
prevalence, timing, or directionality by construction.

```python
# Same pipeline, different data
analyzer_null = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct_null,
    identity_a      = "simul3_event_x",
    identity_b      = "simul3_event_y",
)

presence_null = analyzer_null.compute_presence()
print(presence_null)
```

```
EventCoOccurrencePresenceResult:
  identity_a        : simul3_event_x
  identity_b        : simul3_event_y
  entities          : 5,000
  ────────────────────────────────────────────
  n_with_a          : 1,298 (26.0%)
  n_with_b          : 1,273 (25.5%)
  n_with_both       : 335   (6.7%)
  n_with_neither    : 2,764 (55.3%)
  ────────────────────────────────────────────
  p_b_given_a       : 25.8%
  p_b_given_no_a    : 25.3%
  prevalence_ratio  : 1.019×
  ────────────────────────────────────────────
  fisher_exact_p    : 0.7391
```

`p_b_given_a` = 25.8% ≈ `p_b_given_no_a` = 25.3% — having event X
provides no information about whether a patient also had event Y.
The prevalence ratio of 1.019 (CI: 0.92–1.13 crosses 1.0) and Fisher
p=0.74 confirm there is no signal.

**The contrast:**

| | simul_1 (signal) | simul_3 (null) |
|---|---|---|
| P(B\|A) | 62.2% | 25.8% |
| P(B\|no A) | 36.5% | 25.3% |
| Prevalence ratio | 1.706× | 1.019× |
| Fisher p | 1.27e-06 | 0.74 (n.s.) |

The same code, the same analyzer, the same result object — two
completely different scientific conclusions. The tool is working.

---

## What this demonstrated

- **Co-occurrence counting is a first-class operation** —
  `EventCoOccurrenceAnalyzer` receives the `CohortTimeline` directly.
  Both event streams are already there, already validated, already
  namespaced by identity. No per-entity merge to engineer. No date
  string parsing to write.

- **The denominator is validated at construction** — the reference
  population is the full 5,000-patient `CohortTimeline`. All four
  cells of the 2×2 table are correct. The "neither" cell is computed
  automatically from the full declared cohort, not from the
  intersection of the event DataFrames.

- **The full cohort is declared, not inferred** — `ObsPeriodPerEntity`
  is constructed from the full patient pool before either event stream
  is consulted. Deriving the patient list from event DataFrames silently
  drops patients with neither event and produces wrong association
  measures — a silent correctness error that eventus makes impossible
  by design.

- **`EventCoOccurrencePresenceResult` solves the column-naming
  problem** — `p_b_given_a`, `p_b_given_no_a`, `prevalence_ratio`,
  and `fisher_exact_p` are named, documented properties of a validated
  object. The Fisher's exact p-value is always computed and always
  consistent with the 2×2 table — the researcher never has to import
  `scipy`, remember the correct contingency array format, or worry
  about whether the test matches the table.

- **The disclaimer is part of the result** — `presence.association.disclaimer`
  states clearly that these measures describe co-occurrence patterns
  within a defined observation period — not mechanisms, not directionality,
  not clinical relationships. The package is designed for observational
  studies and the language reflects that throughout.

- **Both streams cleaned independently, assembled once** — separate
  semantics, separate cleaner configs, separate audit reports. The
  `CohortTimeline` assembler does not know how either stream was
  cleaned. It receives validated objects and trusts them.

---

*The next chapter asks a different question: among patients who had
both events, how long between them — and is that gap shorter than
chance would predict?*
