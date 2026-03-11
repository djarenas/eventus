## Why Separate Distribution Selection from Covariate Modeling

When analyzing count data with covariates, a naive approach would fit every
combination of count model and covariate set simultaneously — 9 distributional
forms times all possible covariate subsets creates a combinatorial explosion
that is computationally prohibitive and statistically questionable due to
multiple testing.

This framework addresses the problem through a two-step workflow. In the first
step, the intercept-only layer (CountDistributionMenu, CountDistributionFitters,
and CountsFitResult) fits all candidate count distributions to the raw counts
without any covariates. Information criteria (AIC, BIC) identify the top 2–3
distributional forms that best capture the data's structure — its dispersion
pattern, zero-inflation behavior, or mixture characteristics. In the second
step, the regression layer (CountRegressionFitters and RegressionFitResult)
adds covariates only to these top candidates, estimating coefficients and
comparing effect sizes across the surviving models.

This separation is both practical and principled. It reduces the search space
from a combinatorial explosion to a manageable two-stage process. It also
reflects a natural modeling logic: first understand the shape of the count
distribution (Is there overdispersion? Zero-inflation? Subpopulations?), then
ask which person-level or event-level features drive variation within that
distributional form. If the top 2–3 models yield similar covariate effect sizes,
the findings are robust to distributional assumptions. If effect sizes diverge
across models, that itself is an important finding — it signals that
conclusions about covariates depend on the assumed count distribution, and
further investigation is warranted.

The architecture supports this workflow by design. The intercept-only classes
(CountDistribution, CountDistributionFitter, CountsFitResult) operate
independently of the regression classes (CountRegressionDistribution,
CountRegressionFitter, RegressionFitResult). EventsWithCovariates inherits
from Events, so it works seamlessly with both layers. A researcher can complete
step one, examine results, and only then proceed to step two — without
rewriting code or restructuring data.

YAML configuration plays a central role in making this workflow reproducible and
auditable. Both the CountDistributionMenu and CovariateSemantics are built from
YAML files, which means every decision — which models were considered, which
covariates were included, how categorical variables were encoded, how event-level
features were aggregated — is captured in a human-readable configuration file
that can be version-controlled, shared with collaborators, and revisited months
or years later. A researcher can return to a completed analysis, open the YAML,
and see exactly what was done without reading code. The menu abstraction makes
it particularly easy to iterate: adding or removing a candidate model is a
one-line edit in the YAML, not a code change. Running the same study with a
different set of models, or handing the configuration to a colleague to
reproduce the analysis on a different dataset, requires no programming — just
a YAML file and the data.
