# eventus.analyzers.event_cooccurrence

Co-occurrence analyzers for two event identities within a `CohortTimeline`.
This subfolder implements a three-tier architecture across three analytical
dimensions: presence (chapter 8), gap timing (chapter 9), and directionality
(chapter 10).

---

## Architecture

```
EventCoOccurrenceAnalyzer          — first-level: takes CohortTimeline
    ↓ compute_presence()
EventCoOccurrencePresenceResult    — intermediate
    ↓
EventCoOccurrenceAssociation       — derived cohort-level object

    ↓ compute_gaps()
EventCoOccurrenceGapSummary        — intermediate (per-entity)
    ↓
EventCoOccurrenceGapAnalyzer       — second-level: takes GapSummary
    ↓ compute_test()
EventCoOccurrenceGapTest           — intermediate (cohort-level)

    ↓ compute_directionality()
EventCoOccurrenceDirectionalitySummary  — intermediate (per-entity)
    ↓
EventCoOccurrenceDirectionalityAnalyzer — second-level: takes DirectionalitySummary
    ↓ compute_test()
EventCoOccurrenceDirectionalityTest     — intermediate (cohort-level)
```

Second-level analyzers take a validated intermediate as input rather
than a `CohortTimeline`. The validated per-entity summary is already
structurally sound — the second-level analyzer adds only the statistical
layer without re-reading any raw data.

---

## `EventCoOccurrenceAnalyzer`

First-level analyzer. Takes a `CohortTimeline` and produces per-entity
summary objects for each of the three analytical dimensions.

```python
from eventus.analyzers import EventCoOccurrenceAnalyzer

analyzer = EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "cirrhosis_diagnosis",
    identity_b      = "ed_visit",
)
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `identity_a` or `identity_b` not in `cohort_timeline.event_identities`
- `identity_a == identity_b`

### `compute_presence()` → `EventCoOccurrencePresenceResult`

Per-entity binary presence flags. Answers: do A and B co-occur in
the same observation period above what chance would predict?

```python
presence = analyzer.compute_presence()
print(presence)
# → p_b_given_a, p_b_given_no_a, prevalence_ratio, fisher_exact_p
```

Access the full association object (lazily computed, cached):

```python
assoc = presence.association
print(assoc)
# → 2×2 table, conditional probabilities, prevalence ratio with CIs
```

### `compute_gaps()` → `EventCoOccurrenceGapSummary`

Per-entity absolute nearest-neighbor gaps in both directions. Answers:
how close are A and B events in time — and is that proximity shorter
than chance would predict?

Gap is direction-agnostic — for each A event, the nearest B in either
direction is found. The median across all A events for each entity is
stored.

```python
gaps = analyzer.compute_gaps()
print(gaps)
# → cohort_median_a_to_b, cohort_median_b_to_a
```

### `compute_directionality()` → `EventCoOccurrenceDirectionalitySummary`

Per-entity mean signed gaps. Answers: does A tend to come before B,
or is the ordering random?

Signed gap: positive if B is after A, negative if before. Mean across
all A events for each entity — contrast with `compute_gaps()` which
uses absolute median. Different questions, different aggregation strategies.

```python
directionality = analyzer.compute_directionality()
print(directionality)
# → n_a_first, n_b_first, fraction_a_first, cohort_mean_signed_gap
```

---

## `EventCoOccurrenceGapAnalyzer`

Second-level analyzer. Takes an `EventCoOccurrenceGapSummary` and
produces an `EventCoOccurrenceGapTest` via permutation null.

```python
from eventus.analyzers import EventCoOccurrenceGapAnalyzer

gaps     = analyzer.compute_gaps()
gap_test = EventCoOccurrenceGapAnalyzer(gaps).compute_test(n_permutations=500)
print(gap_test)
# → observed median, null median, KS statistic, KS p, gap_ratio
```

### The permutation null

For each permutation, for each co-occurring entity:
- Draw `n_a` new A dates uniformly from `[obs_start, obs_end]`
- Draw `n_b` new B dates uniformly from `[obs_start, obs_end]`
- Recompute nearest gap A→B and B→A
- Take median across events

This preserves each entity's event counts and observation window while
destroying any temporal relationship between A and B.

### `gap_ratio`

`observed_median / null_median`. Values < 1 mean observed gaps are
shorter than independence predicts — temporal clustering. Values ≈ 1
mean no temporal signal.

```
gap_ratio = 0.45  → observed gaps are ~half what independence predicts
gap_ratio = 1.02  → no temporal signal
```

---

## `EventCoOccurrenceDirectionalityAnalyzer`

Second-level analyzer. Takes an `EventCoOccurrenceDirectionalitySummary`
and produces an `EventCoOccurrenceDirectionalityTest` via permutation null
and Wilcoxon signed-rank test.

```python
from eventus.analyzers import EventCoOccurrenceDirectionalityAnalyzer

dir_summary = analyzer.compute_directionality()
dir_test    = EventCoOccurrenceDirectionalityAnalyzer(dir_summary).compute_test(
    n_permutations=500
)
print(dir_test)
# → fraction_a_first, null_fraction_a_first, direction_ratio,
#   wilcoxon_statistic, wilcoxon_p
```

### The permutation null

Same logic as `EventCoOccurrenceGapAnalyzer` — shuffle both A and B
dates uniformly within each entity's observation window. The null
`fraction_a_first` is computed empirically, not assumed to be 0.50.

### `direction_ratio`

`observed_fraction_a_first / null_fraction_a_first`. Values > 1 mean
A precedes B more than independence predicts. Values ≈ 1 mean no
directional signal.

```
direction_ratio = 1.24  → A precedes B 24% more than chance predicts
direction_ratio = 1.06  → no meaningful directional signal
```

---

## Statistical disclaimer

The permutation null, KS test, and Wilcoxon signed-rank test implemented
here are illustrative of the eventus analytical architecture. They have
not been formally evaluated for Type I error control or statistical power
under real administrative claims data conditions. See
`ch8-12_simulation_design.md` for the full statistical disclaimer.

The architecture is designed to make formal validation and substitution
straightforward — the permutation mechanism, test statistic, and
aggregation strategy can each be replaced independently without changing
any other component.

---

## Internal utils

| File | Contains |
|---|---|
| `event_co_occurrence_primitives.py` | `parse_event_dates()`, `build_co_occurrence_streams()`, `nearest_forward_gaps()`, `gap_stats()` — shared across all co-occurrence utils |
| `event_co_occurrence_presence_utils.py` | Per-entity binary presence computation |
| `event_co_occurrence_gap_utils.py` | Per-entity absolute nearest-neighbor gap computation |
| `event_co_occurrence_directionality_utils.py` | Per-entity mean signed gap computation |
