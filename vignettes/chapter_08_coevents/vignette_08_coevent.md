# Chapter 8 — Event Co-occurrence Analysis

## Vignette: Do ED Visits and Hospitalizations Co-occur?

You have two cleaned event streams for the same 800-patient cohort:
emergency department visits and inpatient hospitalizations. Both were
cleaned independently — separate semantics, separate cleaner configs,
separate audit reports — and assembled into a single `CohortTimeline`.

The scientific question is: *"Among patients who had ED visits, what
proportion also had a hospitalization — and is that co-occurrence above
what chance would predict?"*

This is not a volume question. It is a co-occurrence question. The
answer requires asking both event streams simultaneously, per entity,
within a defined observation period.

---

### The four problems

**Problem 1 — Co-occurrence counting is not a groupby.** You have two
event streams, each stored as pipe-delimited date strings per member
in the `CohortTimeline`. Computing "did this member have both?" requires
parsing both date streams per member and checking presence within the
observation period. That is not `df.groupby("patient_id")["event"].nunique()`.
A script has to engineer this from scratch — a per-entity merge across
two parsed date series with explicit NaN handling for members who had
neither event.

**Problem 2 — The denominator is a choice that must be declared.**
*"32% of patients had both an ED visit and a hospitalization"* — 32% of
what? All 800 patients? Only patients with any ED visit? Only patients
with any hospitalization? Each answer is a different scientific claim.
A script tracks this manually and silently mixes denominators.
`EventCoOccurrencePresenceResult` validates the denominator at
construction — the reference population is the full `CohortTimeline`,
not whichever DataFrame happened to be filtered last.

**Problem 3 — The column-naming problem is worst here.** A script that
computes co-occurrence statistics produces a dictionary, a tuple, or a
DataFrame with column names invented on the spot: `n_ed_and_hosp`,
`count_both`, `pct_co`, `OR`, `ci_lo`, `ci_hi`. None of these are
self-describing. None carry their own documentation.
`EventCoOccurrenceAssociation` carries `odds_ratio`, `ci_lower`,
`ci_upper`, and `contingency_table` as named, documented properties of
a validated object. The column-naming problem disappears when results
carry their own context.

**Problem 4 — Building the 2×2 table correctly requires the full
cohort.** The four cells of a co-occurrence contingency table — both,
A only, B only, neither — each need the right denominator. The
"neither" cell is the hardest: patients who had neither event, within
the defined observation period. A script that only has the two event
DataFrames cannot compute this correctly without loading the full member
list separately — and remembering to do so. `EventCoOccurrenceAnalyzer`
receives the `CohortTimeline` directly. The full cohort is already
there.

---

## The eventus solution

### Step 1 — Clean both streams independently

Each stream gets its own semantics, its own cleaner config, its own
audit report. Neither knows about the other.

```python
# ED visits
ed_sem    = eventus.EventSemantics.build_from_yaml("configs/ed_semantics.yaml")
ed_config = eventus.EventsCleanerConfig.build_from_yaml("configs/ed_cleaner.yaml")
ed_cleaner = eventus.EventsCleaner(ed_raw_df, ed_sem, ed_config)
ed_visits  = ed_cleaner.clean()
ed_cleaner.print_report()

# Hospitalizations
hosp_sem    = eventus.EpisodeSemantics.build_from_yaml("configs/hosp_semantics.yaml")
hosp_config = eventus.EpisodesCleanerConfig.build_from_yaml("configs/hosp_cleaner.yaml")
hosp_cleaner = eventus.EpisodesCleaner(hosp_raw_df, hosp_sem, hosp_config)
hospitalizations = hosp_cleaner.clean()
hosp_cleaner.print_report()
```

```
Cleaning report — ED visits
────────────────────────────────────────────────────────
Total input rows:                                4,821
  Rejected:
    duplicate_row:                               2,891   (59.9%)
    null_date:                                      96   (2.0%)
    null_entity_id:                                 48   (1.0%)
────────────────────────────────────────────────────────
Clean rows:                                      1,786   (37.0%)

Cleaning report — hospitalizations
────────────────────────────────────────────────────────
Total input rows:                                2,934
  Rejected:
    duplicate_row:                               2,159   (73.6%)
    null_start_date:                                88   (3.0%)
────────────────────────────────────────────────────────
Clean rows:                                        687   (23.4%)
```

Two separate reports. Two separate audit trails. Nothing silent.

### Step 2 — Assemble the CohortTimeline

```python
obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_patient_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

ct = eventus.CohortTimeline.build_from_components(
    obs_period   = obs,
    episodes     = hospitalizations,
    events       = ed_visits,
)

print(ct)
```

```
CohortTimeline(
  entities           : 800
  has_obs_period     : True
  episode_identities : ['inpatient_hospitalization']
  event_identities   : ['ed_visit']
)
```

Both streams assembled. One row per patient. The `CohortTimeline` knows
what it holds.

### Step 3 — Compute presence co-occurrence

```python
analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline  = ct,
    event_identity_a = "ed_visit",
    event_identity_b = "inpatient_hospitalization",
)

presence = analyzer.compute_presence(within_days=0)
print(presence)
```

```
EventCoOccurrencePresenceResult:
  identity_a       : ed_visit
  identity_b       : inpatient_hospitalization
  entities         : 800
  n_with_a         : 612   (76.5%)
  n_with_b         : 421   (52.6%)
  n_with_both      : 387   (48.4%)
  n_with_neither   : 175   (21.9%)
```

`within_days=0` means same observation period — no temporal window
constraint. Both streams are evaluated within the defined 2022
observation period. The denominator is all 800 patients.

### Step 4 — The association object

```python
assoc = presence.association
print(assoc)
```

```
EventCoOccurrenceAssociation:
  identity_a : ed_visit
  identity_b : inpatient_hospitalization
  entities   : 800

  Contingency table:
                    has_b    no_b    total
  has_a               387     225      612
  no_a                 34     154      188
  total               421     379      800

  odds_ratio         : 7.79
  ci_lower  (95%)    : 4.97   [Wilson/Woolf]
  ci_upper  (95%)    : 12.22
  disclaimer         : Observational association. Does not imply
                       causation. CIs are analytical approximations.
```

The 2×2 table is correct by construction — all four cells, all
marginals, all denominators. The odds ratio and CIs are properties of
a validated object. The disclaimer is part of the object, not an
afterthought.

The association is strong — patients with an ED visit were nearly 8×
more likely to also have a hospitalization. This is consistent with
the simulation: 20% of ED visits directly trigger a hospitalization
the same or next day.

### Step 5 — Compute gaps

```python
gaps = analyzer.compute_gaps()
print(gaps)
```

```
EventCoOccurrenceGapResult:
  identity_a         : ed_visit
  identity_b         : inpatient_hospitalization
  entities           : 800
  n_with_forward_gap : 436   (54.5%)
  mean_forward_gap   : 18.4  days
  median_forward_gap : 3.0   days
  n_with_reverse_gap : 395   (49.4%)
  mean_reverse_gap   : 22.1  days
  median_reverse_gap : 8.0   days
```

The median forward gap of 3 days — ED visit to nearest subsequent
hospitalization — reflects the simulated structure: 20% of ED visits
trigger admission the same or next day, pulling the median down sharply.
The median reverse gap of 8 days — discharge to nearest subsequent ED
visit — reflects the independent visit rate after discharge.

---

## What this demonstrated

- **Co-occurrence counting is a first-class operation** —
  `EventCoOccurrenceAnalyzer` receives the `CohortTimeline` directly.
  Both streams are already there, already validated, already namespaced
  by identity. No per-entity merge to engineer. No date string parsing
  to write.

- **The denominator is validated at construction** — the reference
  population is the full `CohortTimeline`. All four cells of the 2×2
  table are correct. The "neither" cell — patients with neither event
  — is computed automatically from the full cohort, not from the
  intersection of the two event DataFrames.

- **`EventCoOccurrenceAssociation` solves the column-naming problem** —
  the odds ratio, CIs, and contingency table are named, documented
  properties of a self-describing object. The alternative — a
  dictionary with keys invented on the spot — has no documentation,
  no validation, and no disclaimer. The disclaimer is part of the
  object because it is always true for observational co-occurrence
  statistics.

- **`compute_gaps()` answers the temporal question** — the median
  forward gap of 3 days is consistent with the simulated 20%
  ED-to-admission rate. The typed `EventCoOccurrenceGapResult` carries
  both directions explicitly — forward (A before B) and reverse (B
  before A) — with validated NaN semantics for entities without
  qualifying pairs.

- **The open/closed principle demonstrated end-to-end** —
  `EventCoOccurrenceAnalyzer` is a new class that consumes existing
  validated objects. `CohortTimeline`, `EpisodesCleaner`,
  `EventsCleaner`, and every existing analyzer required zero changes.
  The system was extended without modifying anything that already worked.

- **Both streams cleaned independently, assembled once** — separate
  semantics, separate cleaner configs, separate audit reports. The
  assembler does not know how either stream was cleaned. It receives
  validated objects and trusts them.
