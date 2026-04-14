"""Counts fit result.

A CountsFitResult holds count data and a collection of fitted
distributions. It can compute fit metrics, rank distributions,
produce summaries, and generate comparison plots.

It does not fit anything — that is the fitter's job. It receives
a CountDistributionCollection and evaluates how well each
distribution matches the data.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chisquare

from .count_distributions import CountDistribution, PoissonMixtureDistribution
from .count_distribution_collection import CountDistributionCollection
from .model_registry import MODEL_REGISTRY, DISTRIBUTION_TO_MODEL


class CountsFitResult:
    """The outcome of fitting one or more distributions to count data.

    Holds the count data and a collection of fitted distributions.
    Provides methods to compute metrics, rank models, and generate
    comparison plots.

    Attributes:
        counts (pd.Series): The count data that was fitted.
        collection (CountDistributionCollection): The fitted
            distributions to compare.

    Example:
        >>> collection = CountDistributionCollection(fitted)
        >>> result = CountsFitResult(counts, collection)
        >>> print(result.summarize())
        >>> result.plot_all_fits()
        >>> print(result.best_distribution())
    """

    _ERROR_PREFIX = "[CountsFitResult]"

    # Attribute Declarations
    counts: pd.Series
    collection: CountDistributionCollection

    def __init__(self, counts: pd.Series, collection: CountDistributionCollection):
        """Create a fit result from counts and a collection of distributions.

        Args:
            counts: Count data as pd.Series, np.ndarray, or list.
                Converted to pd.Series internally.
            collection: A validated CountDistributionCollection.

        Raises:
            TypeError: If counts or collection are wrong types.
            ValueError: If counts is empty, has nulls, or negatives.
        """
        counts = self._validate_and_convert_counts(counts)
        self._validate_collection(collection)
        self.counts = counts
        self.collection = collection

    @classmethod
    def _validate_and_convert_counts(cls, counts) -> pd.Series:
        """Validate and convert count data to pd.Series.

        Accepts pd.Series, np.ndarray, or list. Converts to
        pd.Series for consistent downstream use in plotting
        and metrics.

        Args:
            counts: Array-like of counts.

        Returns:
            Validated pd.Series.

        Raises:
            TypeError: If not a supported type.
            ValueError: If empty, has nulls, or has negatives.
        """
        if isinstance(counts, pd.Series):
            series = counts.copy()
        elif isinstance(counts, np.ndarray):
            series = pd.Series(counts, name="event_count")
        elif isinstance(counts, list):
            series = pd.Series(counts, name="event_count")
        else:
            raise TypeError(
                f"{cls._ERROR_PREFIX} __init__: "
                f"counts must be pd.Series, np.ndarray, or list, "
                f"got {type(counts).__name__}"
            )
        if len(series) == 0:
            raise ValueError(
                f"{cls._ERROR_PREFIX} __init__: "
                f"counts cannot be empty"
            )
        if series.isna().any():
            raise ValueError(
                f"{cls._ERROR_PREFIX} __init__: "
                f"counts contain {series.isna().sum()} null values"
            )
        if (series < 0).any():
            raise ValueError(
                f"{cls._ERROR_PREFIX} __init__: "
                f"counts cannot contain negative values"
            )

        return series

    @classmethod
    def _validate_collection(cls, collection) -> None:
        """Validate the collection.

        Raises:
            TypeError: If not a CountDistributionCollection.
        """
        if not isinstance(collection, CountDistributionCollection):
            raise TypeError(
                f"{cls._ERROR_PREFIX} __init__: "
                f"collection must be CountDistributionCollection, "
                f"got {type(collection).__name__}"
            )

    def _get_computer(self, distribution: CountDistribution):
        """Look up and create the right computer for a distribution.

        Uses the model registry for the lookup.

        Args:
            distribution: A CountDistribution instance.

        Returns:
            The matching computer instance.

        Raises:
            KeyError: If distribution type is not in the registry.
        """
        dist_type = type(distribution)
        if dist_type not in DISTRIBUTION_TO_MODEL:
            raise KeyError(
                f"{self._ERROR_PREFIX} _get_computer: "
                f"No computer registered for {dist_type.__name__}"
            )
        model_name = DISTRIBUTION_TO_MODEL[dist_type]
        computer_class = MODEL_REGISTRY[model_name]["computer"]
        return computer_class(distribution)

    def _count_params(self, distribution: CountDistribution) -> int:
        """Count the free parameters of a distribution.

        Handles the special case of PoissonMixture where k is a
        hyperparameter, not a fitted parameter.

        Args:
            distribution: A CountDistribution instance.

        Returns:
            Number of free parameters.
        """
        if isinstance(distribution, PoissonMixtureDistribution):
            return 2 * distribution.params["k"] - 1
        return len(distribution.params)

    # ---- Metrics ----

    def compute_fit_metrics(self) -> pd.DataFrame:
        """Compute AIC, AICc, BIC, and log-likelihood for each distribution.

        Returns:
            DataFrame sorted by AIC with columns:
            model, n_params, log_likelihood, aic, aicc, bic
        """
        n = len(self.counts)
        k_values = self.counts.values
        rows = []

        for name, dist in self.collection:
            computer = self._get_computer(dist)
            pmf_vals = computer.compute_pmf(k_values)
            log_lik = float(np.sum(np.log(pmf_vals + 1e-10)))

            n_params = self._count_params(dist)

            aic = 2 * n_params - 2 * log_lik
            aicc = aic + (2 * n_params ** 2 + 2 * n_params) / max(n - n_params - 1, 1)
            bic = n_params * np.log(n) - 2 * log_lik

            rows.append({
                "model": name,
                "n_params": n_params,
                "log_likelihood": round(log_lik, 4),
                "aic": round(aic, 4),
                "aicc": round(aicc, 4),
                "bic": round(bic, 4),
            })

        df = pd.DataFrame(rows).sort_values("aic").reset_index(drop=True)
        return df

    def compute_goodness_of_fit(self) -> pd.DataFrame:
        """Run chi-square goodness of fit test for each distribution.

        Automatically bins small expected values to ensure test
        validity.

        Returns:
            DataFrame with columns: model, chi2_stat, p_value
        """
        k_range = np.arange(0, self.counts.max() + 1)
        n = len(self.counts)
        rows = []

        observed = np.array([
            (self.counts == k).sum() for k in k_range
        ])

        for name, dist in self.collection:
            computer = self._get_computer(dist)
            expected = computer.compute_pmf(k_range) * n

            # Normalize expected to match observed total
            expected = expected * (observed.sum() / expected.sum())

            # Bin small expected values
            obs_binned = observed.copy().astype(float)
            exp_binned = expected.copy()
            min_expected = 5
            while len(exp_binned) > 1 and exp_binned[-1] < min_expected:
                exp_binned[-2] += exp_binned[-1]
                obs_binned[-2] += obs_binned[-1]
                exp_binned = exp_binned[:-1]
                obs_binned = obs_binned[:-1]

            n_params = self._count_params(dist)

            try:
                stat, p_value = chisquare(obs_binned, exp_binned, ddof=n_params)
                rows.append({
                    "model": name,
                    "chi2_stat": round(float(stat), 4),
                    "p_value": round(float(p_value), 4),
                })
            except Exception:
                rows.append({
                    "model": name,
                    "chi2_stat": np.nan,
                    "p_value": np.nan,
                })

        return pd.DataFrame(rows)

    def best_distribution(self, criterion: str = "aic") -> str:
        """Return the name of the best-fitting distribution.

        Args:
            criterion: 'aic', 'aicc', or 'bic'.

        Returns:
            Name of the distribution with the lowest score.

        Raises:
            ValueError: If criterion is not recognized.
        """
        valid = {"aic", "aicc", "bic"}
        if criterion not in valid:
            raise ValueError(
                f"{self._ERROR_PREFIX} best_distribution: "
                f"criterion must be one of {valid}, got '{criterion}'"
            )

        metrics = self.compute_fit_metrics()
        best_row = metrics.sort_values(criterion).iloc[0]
        return best_row["model"]

    # ---- Display ----

    def summarize(self, criterion: str = "aic") -> str:
        """Generate a human-readable summary of the comparison.

        Includes rankings, best model, delta scores, and each
        distribution's self-description.

        Args:
            criterion: 'aic', 'aicc', or 'bic' for ranking.

        Returns:
            Formatted multi-line string.
        """
        metrics = self.compute_fit_metrics().sort_values(criterion).reset_index(drop=True)
        gof = self.compute_goodness_of_fit()
        best_name = metrics.iloc[0]["model"]
        best_score = metrics.iloc[0][criterion]

        lines = [
            f"{'=' * 65}",
            f"  Counts Fit Result Summary ({criterion.upper()})",
            f"{'=' * 65}",
            f"  N observations: {len(self.counts)}",
            f"  Mean: {self.counts.mean():.4f}",
            f"  Variance: {self.counts.var():.4f}",
            f"  Models compared: {len(self.collection)}",
            f"  Best model: {best_name}",
            f"",
            f"  Rankings:",
        ]

        for _, row in metrics.iterrows():
            delta = row[criterion] - best_score
            marker = " <<<" if row["model"] == best_name else ""
            tied = " (tied)" if 0 < delta <= 2 else ""
            lines.append(
                f"    {row['model']:<40s} "
                f"{criterion.upper()}={row[criterion]:>10.2f}  "
                f"d{criterion.upper()}={delta:>7.2f}"
                f"{tied}{marker}"
            )

        # Each distribution's description
        lines.extend(["", "  Distribution Descriptions:"])
        for name in metrics["model"]:
            dist = self.collection.get(name)
            lines.append(f"")
            lines.append(f"    {name}:")
            for desc_line in dist.describe():
                lines.append(f"      {desc_line}")

        # Goodness of fit
        lines.extend(["", "  Goodness of Fit:"])
        for _, row in gof.iterrows():
            lines.append(
                f"    {row['model']:<40s} "
                f"chi2={row['chi2_stat']:>10.4f}  "
                f"p={row['p_value']:.4f}"
            )

        lines.append(f"{'=' * 65}")
        return "\n".join(lines)

    def plot_all_fits(self, show: bool = True, save_to: str = None):
        """Plot observed vs fitted distribution for all models.

        Creates a grid of subplots, one per distribution, ordered
        by AIC ranking.

        Args:
            show: If True, calls plt.show().
            save_to: Optional filepath to save the figure.

        Returns:
            The matplotlib Figure object.
        """
        metrics = self.compute_fit_metrics()
        n_models = len(self.collection)
        n_cols = min(3, n_models)
        n_rows = (n_models + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        if n_models == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        k_range = np.arange(0, self.counts.max() + 1)
        observed_counts = self.counts.value_counts().sort_index()
        observed_freq = observed_counts / len(self.counts)
        best_name = metrics.iloc[0]["model"]

        for i, (_, row) in enumerate(metrics.iterrows()):
            name = row["model"]
            dist = self.collection.get(name)
            computer = self._get_computer(dist)

            ax = axes[i]
            ax.bar(observed_freq.index, observed_freq.values,
                   alpha=0.5, label="Observed", color="steelblue")

            theoretical = computer.compute_pmf(k_range)
            ax.plot(k_range, theoretical,
                    "o-", color="red", label="Fitted", markersize=5)

            title = f"{name}"
            if name == best_name:
                title += " (BEST)"
                ax.set_title(title, fontweight="bold")
            else:
                ax.set_title(title)

            ax.set_xlabel("Events per Person")
            ax.set_ylabel("Probability")
            ax.legend()

        for j in range(n_models, len(axes)):
            axes[j].set_visible(False)

        plt.tight_layout()

        if save_to:
            fig.savefig(save_to, dpi=300, bbox_inches="tight")
        if show:
            plt.show()

        return fig

    def plot_fits_overlay(self, show: bool = True, save_to: str = None):
        """Plot all fitted distributions overlaid on one plot.

        Shows the observed histogram in the background with each
        fitted PMF as a colored line. Best model is drawn thicker.
        Good for at-a-glance comparison of where models diverge.

        Args:
            show: If True, calls plt.show().
            save_to: Optional filepath to save the figure.

        Returns:
            The matplotlib Axes object.
        """
        metrics = self.compute_fit_metrics()
        best_name = metrics.iloc[0]["model"]

        fig, ax = plt.subplots(figsize=(10, 6))

        k_range = np.arange(0, self.counts.max() + 1)
        observed_counts = self.counts.value_counts().sort_index()
        observed_freq = observed_counts / len(self.counts)

        # Observed bars in background
        ax.bar(observed_freq.index, observed_freq.values,
               alpha=0.3, label="Observed", color="steelblue", width=0.8)

        # Color cycle for fitted lines
        colors = plt.cm.Set1(np.linspace(0, 1, len(self.collection)))

        for i, (_, row) in enumerate(metrics.iterrows()):
            name = row["model"]
            dist = self.collection.get(name)
            computer = self._get_computer(dist)
            theoretical = computer.compute_pmf(k_range)

            is_best = name == best_name
            linewidth = 3 if is_best else 1.5
            label = f"{name} (BEST)" if is_best else name

            ax.plot(k_range, theoretical, "o-",
                    color=colors[i], label=label,
                    markersize=4 if is_best else 3,
                    linewidth=linewidth,
                    alpha=1.0 if is_best else 0.7)

        ax.set_xlabel("Events per Person")
        ax.set_ylabel("Probability")
        ax.set_title("All Models vs Observed")
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        plt.tight_layout()

        if save_to:
            fig.savefig(save_to, dpi=300, bbox_inches="tight")
        if show:
            plt.show()

        return ax

    def plot_all_qq(self, show: bool = True, save_to: str = None):
        """QQ plots for all distributions in a grid.

        Args:
            show: If True, calls plt.show().
            save_to: Optional filepath to save the figure.

        Returns:
            The matplotlib Figure object.
        """
        metrics = self.compute_fit_metrics()
        n_models = len(self.collection)
        n_cols = min(3, n_models)
        n_rows = (n_models + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        if n_models == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        n = len(self.counts)
        sorted_data = np.sort(self.counts.values)
        probabilities = (np.arange(1, n + 1) - 0.5) / n
        best_name = metrics.iloc[0]["model"]

        for i, (_, row) in enumerate(metrics.iterrows()):
            name = row["model"]
            dist = self.collection.get(name)
            computer = self._get_computer(dist)

            ax = axes[i]
            theoretical_quantiles = computer.compute_ppf(probabilities)

            ax.scatter(theoretical_quantiles, sorted_data,
                       alpha=0.6, color="steelblue", edgecolors="white", s=40)

            min_val = min(theoretical_quantiles.min(), sorted_data.min())
            max_val = max(theoretical_quantiles.max(), sorted_data.max())
            ax.plot([min_val, max_val], [min_val, max_val],
                    "r--", linewidth=1, label="Perfect fit")

            title = f"{name} QQ"
            if name == best_name:
                title += " (BEST)"
                ax.set_title(title, fontweight="bold")
            else:
                ax.set_title(title)

            ax.set_xlabel("Theoretical Quantiles")
            ax.set_ylabel("Observed Quantiles")
            ax.legend()

        for j in range(n_models, len(axes)):
            axes[j].set_visible(False)

        plt.tight_layout()

        if save_to:
            fig.savefig(save_to, dpi=300, bbox_inches="tight")
        if show:
            plt.show()

        return fig

    def plot_aic_comparison(self, criterion: str = "aic",
                            show: bool = True, save_to: str = None):
        """Bar chart comparing information criterion across models.

        Args:
            criterion: 'aic', 'aicc', or 'bic'.
            show: If True, calls plt.show().
            save_to: Optional filepath to save the figure.

        Returns:
            The matplotlib Axes object.
        """
        metrics = self.compute_fit_metrics().sort_values(criterion).reset_index(drop=True)
        best_name = metrics.iloc[0]["model"]
        best_score = metrics.iloc[0][criterion]

        fig, ax = plt.subplots(figsize=(10, max(5, len(metrics) * 0.8)))

        names = metrics["model"].values
        scores = metrics[criterion].values
        deltas = scores - best_score

        colors = ["#2ecc71" if n == best_name else "#3498db" for n in names]

        ax.barh(range(len(names)), deltas, color=colors, alpha=0.8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.set_xlabel(f"Delta {criterion.upper()} (from best)")
        ax.set_title(f"Model Comparison by {criterion.upper()}")
        ax.invert_yaxis()

        for i, (delta, score) in enumerate(zip(deltas, scores)):
            ax.text(delta + 0.5, i, f"{criterion.upper()}={score:.1f}",
                    va="center", fontsize=9)

        plt.tight_layout()

        if save_to:
            fig.savefig(save_to, dpi=300, bbox_inches="tight")
        if show:
            plt.show()

        return ax

    # ---- Access ----

    def get_distribution(self, name: str) -> CountDistribution:
        """Retrieve a specific distribution by name.

        Args:
            name: The distribution name.

        Returns:
            The CountDistribution instance.

        Raises:
            KeyError: If name is not in the results.
        """
        return self.collection.get(name)

    def __repr__(self) -> str:
        return (
            f"CountsFitResult("
            f"{len(self.collection)} distributions, "
            f"n={len(self.counts)})"
        )

    def __len__(self) -> int:
        return len(self.collection)
