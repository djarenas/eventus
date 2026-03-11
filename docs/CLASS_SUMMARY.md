# Count Models Framework — Class Summary

## Design Philosophy
Every class is a concept. Objects are nouns. Methods are verbs.
If you can't explain it in one sentence, it's not a clean concept.

---

## Layer 1 — Data

### EventSemantics
"A description of what columns mean in event data."
Holds column name mappings. Built from YAML. Validates structure.
Does not hold data.

### Events
"A collection of events that happened to people."
Holds a DataFrame of valid events. Triages bad rows into a
rejected attribute with reasons. Filters by person or date.
Counts events per person.

### CovariateSemantics
"A description of what covariate columns exist, what type they are,
what level (person or event), and how event-level covariates should
be aggregated."
Built from YAML. Validates types, aggregations, interactions.
Does not hold data.

### EventsWithCovariates (inherits from Events)
"Events that have person-level and event-level features attached."
IS an Events — works everywhere Events works. Validates that
covariate columns exist, types are correct, person-level covariates
are constant per person, and person_id matches between event and
covariate semantics.

---

## Layer 2 — Distributions (Intercept-Only)

### CountDistribution (abstract base)
"A mathematical pattern describing how counts are distributed."
Holds parameters. Validates them. Describes itself in plain language.
Does not compute probabilities, fit data, simulate, or plot.

### PoissonDistribution
"All individuals share the same constant event rate."
params: lambda

### PoissonGammaDistribution
"Each individual draws their own rate from a Gamma distribution."
params: alpha (shape), beta (rate)

### GeometricDistribution
"Rates follow an Exponential — maximum heterogeneity."
params: p

### ZIPDistribution
"Some individuals are structural zeros, the rest follow Poisson."
params: pi (zero-inflation), lambda (rate)

### ZIPGDistribution
"Structural zeros plus heterogeneous rates among active individuals."
params: pi, alpha, beta

### GeneralizedPoissonDistribution
"Handles both overdispersion and underdispersion."
params: theta (base rate), lambda (dispersion)

### PoissonMixtureDistribution
"Population consists of K distinct groups with different rates."
params: k, w1..wK (weights), lambda1..lambdaK (rates)

### HurdlePoissonDistribution
"Two stages: cross the hurdle (any events?), then how many."
params: pi (hurdle probability), lambda (rate)

### HurdlePoissonGammaDistribution
"Two stages with heterogeneous rates among those who crossed."
params: pi, alpha, beta

---

## Layer 2 — Simulators (Intercept-Only)

### CountDistributionSimulator (abstract base)
"A tool that generates fake count data from a distribution."
Takes a distribution in its constructor. Has one method:
simulate_counts(n).

### PoissonSimulator, PoissonGammaSimulator, GeometricSimulator,
### ZIPSimulator, ZIPGSimulator, GeneralizedPoissonSimulator,
### PoissonMixtureSimulator, HurdlePoissonSimulator,
### HurdlePoissonGammaSimulator
Each follows its distribution's generative process faithfully.

---

## Layer 2 — Computers (Intercept-Only)

### CountDistributionComputer (abstract base)
"A tool that computes probability quantities from a distribution."
Takes a distribution in its constructor. Computes PMF, PPF,
expected value, variance, survival function.

### PoissonComputer, PoissonGammaComputer, GeometricComputer,
### ZIPComputer, ZIPGComputer, GeneralizedPoissonComputer,
### PoissonMixtureComputer, HurdlePoissonComputer,
### HurdlePoissonGammaComputer
Each knows the specific math for its distribution type.

---

## Layer 3 — Fitting (Intercept-Only)

### CountDistributionFitter (abstract base)
"A tool that estimates a distribution's parameters from count data."
Takes counts via from_events() or from_counts(). Has one method:
fit() which returns a CountDistribution. Stores counts as np.ndarray
for speed.

### PoissonFitter
MLE: lambda = sample mean. Closed-form.

### PoissonGammaFitter
Method of moments, falls back to MLE optimization.

### GeometricFitter
MLE: p = 1 / (1 + mean). Closed-form.

### ZIPFitter
MLE via numerical optimization. Method of moments initialization.

### ZIPGFitter
Three-parameter MLE optimization.

### GeneralizedPoissonFitter
MLE optimization with method of moments initialization.

### PoissonMixtureFitter
EM algorithm. Auto-selects K via BIC if not specified.

### HurdlePoissonFitter
Two-stage: pi from proportion, lambda from zero-truncated MLE.

### HurdlePoissonGammaFitter
Two-stage: pi from proportion, alpha/beta from zero-truncated MLE.

---

## Layer 4 — Organization and Results (Intercept-Only)

### ModelRegistry (model_registry.py)
"The single source of truth mapping model names to their distribution,
fitter, simulator, and computer classes."
MODULE_REGISTRY dict + DISTRIBUTION_TO_MODEL reverse lookup.
Updated once when adding a new model. Everything else reads from it.

### CountDistributionMenu
"A validated set of models to try."
Built from YAML or list of names. Knows the full mapping from name
to distribution/fitter/simulator/computer. Can fit_all(counts) and
generate_permutations() for exhaustive studies.

### CountModelEntry
"One model's full set of classes and optional configuration."
Dataclass holding name, distribution class, fitter class, simulator
class, computer class, and optional config (e.g., k for mixture).

### CountDistributionCollection
"A validated group of distributions with parameters."
Built from fit_all() output or YAML. Can simulate from all
distributions. Saves to and loads from YAML for reproducibility.

### CountsFitResult
"The outcome of fitting multiple distributions to count data."
Takes counts + collection. Computes AIC, AICc, BIC, log-likelihood.
Runs chi-square goodness of fit. Produces comparison plots (grid,
overlay, QQ, bar chart). Summarizes in plain language.

---

## Layer 5 — Regression Specs

### CountRegressionSpec (abstract base)
"What I want a regression model to look like before fitting."
Defines which covariates go into which model component.
Has no coefficients — those come from fitting.

### PoissonRegressionSpec
components: rate

### PoissonGammaRegressionSpec
components: rate, dispersion

### GeometricRegressionSpec
components: rate

### ZIPRegressionSpec
components: rate, zero_inflation

### ZIPGRegressionSpec
components: rate, dispersion, zero_inflation

### GeneralizedPoissonRegressionSpec
components: rate, dispersion

### PoissonMixtureRegressionSpec
components: rate_1..rate_K, weights (variable K)

### HurdlePoissonRegressionSpec
components: hurdle, count

### HurdlePoissonGammaRegressionSpec
components: hurdle, count, dispersion

---

## Layer 5 — Regression Distributions

### CountRegressionDistribution (abstract base)
"A count distribution where the rate depends on covariates."
Holds a spec (the blueprint) and coefficients (the fitted values).
Can describe itself, produce a coefficient table, and export to dict.

### PoissonRegressionDistribution
"rate_i = exp(intercept + b1*age_i + b2*BMI_i + ...)"

### PoissonGammaRegressionDistribution
"rate_i = exp(...), dispersion_i = exp(...)"

### GeometricRegressionDistribution
"rate_i = exp(...), fixed maximum dispersion"

### ZIPRegressionDistribution
"rate_i = exp(...), P(structural zero)_i = logit(...)"

### ZIPGRegressionDistribution
"rate_i = exp(...), dispersion_i = exp(...), P(zero)_i = logit(...)"

### GeneralizedPoissonRegressionDistribution
"rate_i = exp(...), dispersion_i = exp(...)"

### PoissonMixtureRegressionDistribution
"rate_j_i = exp(...) per group, P(group j)_i = softmax(...)"

### HurdlePoissonRegressionDistribution
"P(cross hurdle)_i = logit(...), count_i | crossed = truncPoisson(...)"

### HurdlePoissonGammaRegressionDistribution
"P(cross hurdle)_i = logit(...), count_i = truncPG(...), dispersion_i = exp(...)"

---

## Layer 5 — Regression Collection

### RegressionDistributionCollection
"A validated group of fitted regression distributions."
Holds multiple regression distributions. Produces coefficient
comparison table and stability report. Saves to and loads from YAML.
The primary output for multiverse analysis.

---

## Designed but Not Yet Coded

### PopulationSpec
"What a fake population looks like."
Describes covariate distributions (age ~ Normal(50,15),
county ~ {Cook: 40%, DuPage: 20%, ...}). Built from YAML.

### PopulationGenerator
"Generates a fake covariates DataFrame from a PopulationSpec."
generate(n) → DataFrame of n fake people.

### RegressionSimulator
"Generates fake count data for a population."
Needs a PopulationSpec (what people look like) and a
RegressionDistribution (how covariates affect counts).
simulate(n) → (counts, covariates_df)

### RegressionComputer (or Predictor)
"Computes expected counts for real people."
Takes a RegressionDistribution and a covariates DataFrame.
predict(covariates_df) → predicted rates per person.

### RegressionFitters
"Estimate regression coefficients from EventsWithCovariates."
Take EventsWithCovariates + spec, return RegressionDistribution.
Need helper_design_matrix.py for encoding and interactions.

### RegressionMenu
"A validated set of regression specs to try."
Built from YAML. Holds specs, passes to fitters, collects results.

### RegressionFitResult
"Compare regression models against the same data."
Like CountsFitResult but for regression. AIC/BIC comparison plus
coefficient comparison across models.

### ModelIdentificationStudy
"Tests whether model selection criteria can identify the true model."
Uses collections and menus to run simulation studies.
Produces NxN identification heatmap.

---

## File Structure

```
Layer 1:
    event_semantics.py
    events.py
    covariate_semantics.py
    events_with_covariates.py

Layer 2:
    count_distributions.py
    count_distribution_simulators.py
    count_distribution_computers.py

Layer 3:
    count_distribution_fitters.py
    count_distribution_fitter_zip.py
    count_distribution_fitter_hurdle.py
    count_distribution_fitter_gp.py
    count_distribution_fitter_mixture.py

Layer 4:
    model_registry.py
    count_distribution_menu.py
    count_distribution_collection.py
    counts_fit_result.py

Layer 5:
    count_regression_specs.py
    count_regression_spec_hurdle.py
    count_regression_spec_mixture.py
    count_regression_distributions.py
    count_regression_distribution_hurdle.py
    count_regression_distribution_mixture.py
    regression_distribution_collection.py
```

---

## Key Design Principles

1. Every class is a concept you can explain in one sentence.
2. Objects are nouns. Methods are verbs.
3. A distribution describes. A computer computes. A simulator simulates.
   A fitter fits. Each does one thing.
4. YAML drives configuration for reproducibility.
5. Adding a new model means adding new files, never modifying existing ones.
6. Validation happens at construction — invalid objects cannot exist.
7. Error messages say [ClassName] method_name: what went wrong.
