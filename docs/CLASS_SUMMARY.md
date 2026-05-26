# countmodels — Class Summary

## Design Philosophy
Every class is a concept. Objects are nouns. Methods are verbs.
If you can't explain it in one sentence, it's not a clean concept.
"Regression" only appears in fitters — because fitters do regression.
Everything else describes structure or holds results.

---

## Package Structure

```
countmodels/
├── episodes/
├── distributions/
├── specs/
├── simulators/
├── computers/
├── fitters/
├── collections/
├── results/
├── registry/
└── docs/
```

---

## episodes/

### EpisodeSemantics
"I am a description of what columns mean in episode data."
Holds column name mappings. Built from YAML. Validates structure.
Does not hold data.

### Episodes
"I am a collection of episodes that happened to people."
Holds a DataFrame of valid episodes. Triages bad rows into a
rejected attribute with reasons. Filters by person or date.
Counts episodes per person.

### CovariateSemantics
"I describe what covariate columns exist, what type they are,
what level (person or episode), and how episode-level covariates
should be aggregated."
Built from YAML. Validates types, aggregations, interactions.
Does not hold data.

### EpisodesWithCovariates
"I am Episodes that have person-level and episode-level features attached."
Inherits from Episodes — IS an Episodes. Validates covariate columns
exist, types are correct, person-level covariates are constant
per person, person_id matches between semantics.

### PopulationSpec
"I am a description of a population's characteristics."
Describes distributions of continuous covariates and proportions
of categorical covariates. Built from YAML. Uses a registry of
supported distribution types — no elif chains.

### PopulationGenerator
"I generate fake people based on a population description."
Takes a PopulationSpec. Produces a DataFrame with one row per
person. Supports reproducible generation with seeds.

---

## distributions/

### CountDistribution (abstract base)
"I am a mathematical pattern describing how counts are distributed."
Holds parameters. Validates them. Describes itself in plain language.
Does not compute, fit, simulate, or plot.

File: count_distributions.py (contains all 9 below)

### PoissonDistribution
"All individuals share the same constant episode rate."
params: lambda

### PoissonGammaDistribution
"Each individual draws their own rate from a Gamma distribution."
params: alpha, beta

### GeometricDistribution
"Rates follow an Exponential — maximum heterogeneity."
params: p

### ZIPDistribution
"Some individuals are structural zeros, the rest follow Poisson."
params: pi, lambda

### ZIPGDistribution
"Structural zeros plus heterogeneous rates among active individuals."
params: pi, alpha, beta

### GeneralizedPoissonDistribution
"Handles both overdispersion and underdispersion."
params: theta, lambda

### PoissonMixtureDistribution
"Population consists of K distinct groups with different rates."
params: k, w1..wK, lambda1..lambdaK

### HurdlePoissonDistribution
"Two stages: cross the hurdle, then how many."
params: pi, lambda

### HurdlePoissonGammaDistribution
"Two stages with heterogeneous rates among those who crossed."
params: pi, alpha, beta

### CountCovariateDistribution (abstract base)
"I am a count distribution where parameters depend on covariates."
Holds a spec (the blueprint) and coefficients (the fitted values).
Can describe itself, produce a coefficient table, export to dict.

File: count_covariate_distributions.py (base + Poisson, PoissonGamma,
Geometric, ZIP, ZIPG, GeneralizedPoisson)

File: count_covariate_distribution_hurdle.py (HurdlePoisson, HurdlePoissonGamma)

File: count_covariate_distribution_mixture.py (PoissonMixture)

### PoissonCovariateDistribution
"rate_i = exp(intercept + b1*age_i + b2*BMI_i + ...)"

### PoissonGammaCovariateDistribution
"rate_i = exp(...), dispersion_i = exp(...)"

### GeometricCovariateDistribution
"rate_i = exp(...), fixed maximum dispersion"

### ZIPCovariateDistribution
"rate_i = exp(...), P(structural zero)_i = logit(...)"

### ZIPGCovariateDistribution
"rate_i = exp(...), dispersion_i = exp(...), P(zero)_i = logit(...)"

### GeneralizedPoissonCovariateDistribution
"rate_i = exp(...), dispersion_i = exp(...)"

### PoissonMixtureCovariateDistribution
"rate_j_i = exp(...) per group, P(group j)_i = softmax(...)"

### HurdlePoissonCovariateDistribution
"P(cross hurdle)_i = logit(...), count_i | crossed = truncPoisson(...)"

### HurdlePoissonGammaCovariateDistribution
"P(cross)_i = logit(...), count_i = truncPG(...), dispersion_i = exp(...)"

---

## specs/

### CountCovariateSpec (abstract base)
"I describe which covariates affect which components of a count
distribution."
Has no coefficients. Just structure. Built from code or YAML (via menu).

File: count_covariate_specs.py (base + Poisson, PoissonGamma,
Geometric, ZIP, ZIPG, GeneralizedPoisson)

File: count_covariate_spec_hurdle.py (HurdlePoisson, HurdlePoissonGamma)

File: count_covariate_spec_mixture.py (PoissonMixture)

### PoissonCovariateSpec
components: rate

### PoissonGammaCovariateSpec
components: rate, dispersion

### GeometricCovariateSpec
components: rate

### ZIPCovariateSpec
components: rate, zero_inflation

### ZIPGCovariateSpec
components: rate, dispersion, zero_inflation

### GeneralizedPoissonCovariateSpec
components: rate, dispersion

### PoissonMixtureCovariateSpec
components: rate_1..rate_K, weights (variable K)

### HurdlePoissonCovariateSpec
components: hurdle, count

### HurdlePoissonGammaCovariateSpec
components: hurdle, count, dispersion

---

## simulators/

### CountDistributionSimulator (abstract base)
"I generate fake count data from a distribution."
Takes a distribution in constructor. Has one method: simulate_counts(n).

File: count_distribution_simulators.py (all 9 below)

### PoissonSimulator, PoissonGammaSimulator, GeometricSimulator,
### ZIPSimulator, ZIPGSimulator, GeneralizedPoissonSimulator,
### PoissonMixtureSimulator, HurdlePoissonSimulator,
### HurdlePoissonGammaSimulator
Each follows its distribution's generative process faithfully.

Future: count_covariate_simulators.py

---

## computers/

### CountDistributionComputer (abstract base)
"I compute probability quantities from a distribution."
Takes a distribution in constructor. Computes PMF, PPF,
expected value, variance, survival function.

File: count_distribution_computers.py (all 9 below)

### PoissonComputer, PoissonGammaComputer, GeometricComputer,
### ZIPComputer, ZIPGComputer, GeneralizedPoissonComputer,
### PoissonMixtureComputer, HurdlePoissonComputer,
### HurdlePoissonGammaComputer
Each knows the specific math for its distribution type.

Future: count_covariate_computers.py

---

## fitters/

### CountDistributionFitter (abstract base)
"I estimate a distribution's parameters from count data."
Takes counts via from_episodes() or from_counts(). Returns a
CountDistribution. Stores counts as np.ndarray for speed.

File: count_distribution_fitters.py (base + Poisson, PoissonGamma, Geometric)
File: count_distribution_fitter_zip.py (ZIP, ZIPG)
File: count_distribution_fitter_hurdle.py (HurdlePoisson, HurdlePoissonGamma)
File: count_distribution_fitter_gp.py (GeneralizedPoisson)
File: count_distribution_fitter_mixture.py (PoissonMixture, auto K via BIC)

Future: count_covariate_fitters.py (uses regression internally)

---

## collections/

### CountDistributionCollection
"I am a validated group of distributions with parameters."
Built from fit_all() output or YAML. Can simulate from all
distributions. Saves to and loads from YAML.

### CovariateDistributionCollection
"I am a validated group of fitted covariate distributions."
Holds multiple covariate distributions. Produces coefficient
comparison table and stability report. Saves to and loads from YAML.

---

## results/

### CountsFitResult
"I am the outcome of fitting multiple distributions to count data."
Takes counts + collection. Computes AIC, AICc, BIC. Runs chi-square
goodness of fit. Produces comparison plots (grid, overlay, QQ,
bar chart). Summarizes in plain language.

Future: CovariatesFitResult

---

## registry/

### ModelRegistry (model_registry.py)
"I am the single source of truth mapping model names to their
distribution, fitter, simulator, and computer classes."
MODEL_REGISTRY dict + DISTRIBUTION_TO_MODEL reverse lookup.
Updated once when adding a new model.

### CountDistributionMenu
"I am a validated set of models to try."
Built from YAML or list of names. Knows the full mapping from
name to distribution/fitter/simulator/computer. Can fit_all()
and generate_permutations().

### CountModelEntry
"I am one model's full set of classes and optional configuration."
Dataclass holding name, distribution class, fitter class,
simulator class, computer class, and optional config.

Future: CovariateMenu (holds specs, drives covariate fitting)

---

## Design Principles

1. Every class is a concept you can explain in one sentence.
2. Objects are nouns. Methods are verbs.
3. A distribution describes. A computer computes. A simulator simulates.
   A fitter fits. Each does one thing.
4. "Regression" only appears in fitters — because fitters do regression.
   Everything else just describes structure or holds results.
5. YAML drives configuration for reproducibility.
6. Adding a new model means adding new files, never modifying existing ones.
7. Validation happens at construction — invalid objects cannot exist.
8. Error messages say [ClassName] method_name: what went wrong.
9. File names are fully descriptive — you know what's inside without
   knowing the folder.
10. Folder structure organizes by concept type during development.
    Clean imports for users come later via __init__.py.

---

## Not Yet Coded

### Covariate Simulators
"I generate fake count data for a population where counts depend
on covariates."
Needs: PopulationGenerator + CovariateDistribution.

### Covariate Computers / Predictors
"I compute expected counts for real people given their covariates."
Takes a CovariateDistribution and covariates DataFrame.

### Covariate Fitters
"I estimate covariate distribution coefficients from data."
Takes EpisodesWithCovariates + CovariateSpec, returns
CovariateDistribution. Uses regression internally.
Needs: helper_design_matrix.py for encoding and interactions.

### Covariate Menu
"A validated set of covariate specs to try."
Built from YAML. Holds specs, passes to fitters, collects results.

### Covariate Fit Result
"Compare covariate models against the same data."
AIC/BIC comparison plus coefficient comparison across models.

### Model Identification Study
"Tests whether model selection criteria can identify the true model."
Uses collections and menus to run simulation studies.
Produces NxN identification heatmap.

---

## Two-Step Workflow

Step 1: Find the right count distribution (no covariates)
    Menu → fit_all(counts) → Collection → CountsFitResult
    Pick top 2-3 models by BIC.

Step 2: Add covariates to winning models only
    CovariateMenu → fit_all(episodes_with_covariates) → CovariateCollection
    Compare coefficients across models.
    If effect sizes are stable → robust finding.
    If effect sizes diverge → sensitive to model choice.
