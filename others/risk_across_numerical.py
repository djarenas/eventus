import numpy as np  
import pandas as pd  
import matplotlib.pyplot as plt  
from statistics import NormalDist  
  
  
class RiskAcrossNumerical:  
    """  
    Compute and visualize outcome risk across predefined numerical bins.  
  
    This class validates input data, coerces supported value types, computes  
    bin-level risk, and generates a bar plot of risk percentages.  
  
    **Risk definition**  
        risk_percentage = (true_count / entity_count) * 100  
  
    where:  
    - entity_count = number of entities in a bin  
    - true_count   = number of entities in that bin with outcome=True  
  
    Notes  
    -----  
    - Rows with NaN in any required column are dropped (with a printed warning).  
    - Duplicate entity IDs are not allowed (checked after NaN removal).  
    - Outcome values accepted:  
        - bool: True / False  
        - numeric: 1 / 0  
        - strings: "1", "0", "true", "false" (case-insensitive)  
    - Numerical column allows numeric strings (e.g., "12.5"), which are coerced.  
    - Bins are user-provided edges (e.g., [0, 90, 180, np.inf]) and treated as  
      right-closed intervals: (a, b], with include_lowest=True.  
    - Bins with entity_count < minimum_count_per_bin are excluded from output/plot.  
  
    Parameters  
    ----------  
    df : pandas.DataFrame  
        Input dataset containing entity, outcome, and numerical columns.  
    column_map : dict  
        Mapping of logical names to DataFrame column names.  
        Required keys:  
        - "entity"  
        - "outcome"  
        - "numerical"  
    bins : list-like  
        Strictly increasing bin edges, e.g. [0, 90, 180, np.inf].  
    minimum_count_per_bin : int, optional  
        Minimum number of entities required for a bin to be included.  
        Default is class constant MINIMUM_COUNT_PER_BIN (1).  
  
    Raises  
    ------  
    TypeError  
        If input types are invalid (e.g., df not DataFrame, invalid column types).  
    ValueError  
        If required columns are missing, bins are invalid, duplicate entity IDs exist,  
        or values cannot be coerced to expected formats.  
    """  
  
  
    MINIMUM_COUNT_PER_BIN = 1  
    REQUIRED_COLUMN_KEYS = {"entity", "outcome", "numerical"}  
  
    def __init__(  
        self,  
        df: pd.DataFrame,  
        column_map: dict,  
        bins,  
        minimum_count_per_bin: int = None,  
    ):  
        self._validate_constructor_inputs(df, column_map, bins, minimum_count_per_bin)  
  
        self.df = df.copy()  
        self.column_map = column_map  
        self.entity_col = column_map["entity"]  
        self.outcome_col = column_map["outcome"]  
        self.numerical_col = column_map["numerical"]  
        self.bins = self._validate_bins(bins)  
  
        if minimum_count_per_bin is None:  
            self.minimum_count_per_bin = self.MINIMUM_COUNT_PER_BIN  
        else:  
            self.minimum_count_per_bin = minimum_count_per_bin  
  
        self.cleaned_df = self._prepare_dataframe()  
  
    # -----------------------------  
    # Validators  
    # -----------------------------  
    def _validate_constructor_inputs(self, df, column_map, bins, minimum_count_per_bin):  
        if not isinstance(df, pd.DataFrame):  
            raise TypeError("df must be a pandas DataFrame.")  
  
        if not isinstance(column_map, dict):  
            raise TypeError("column_map must be a dict.")  
  
        missing_keys = self.REQUIRED_COLUMN_KEYS - set(column_map.keys())  
        extra_keys = set(column_map.keys()) - self.REQUIRED_COLUMN_KEYS  
        if missing_keys:  
            raise ValueError(f"column_map missing required keys: {missing_keys}")  
        if extra_keys:  
            raise ValueError(f"column_map has unexpected keys: {extra_keys}")  
  
        for k in self.REQUIRED_COLUMN_KEYS:  
            col = column_map[k]  
            if col not in df.columns:  
                raise ValueError(f"Column '{col}' (mapped from key '{k}') not found in dataframe.")  
  
        if minimum_count_per_bin is not None:  
            if not isinstance(minimum_count_per_bin, int) or minimum_count_per_bin < 1:  
                raise ValueError("minimum_count_per_bin must be an integer >= 1.")  
  
        # bins validated separately for better error messages  
        self._validate_bins(bins)  
  
    def _validate_bins(self, bins):  
        if not isinstance(bins, (list, tuple, np.ndarray, pd.Series)):  
            raise TypeError("bins must be list-like, e.g. [0, 90, 180, np.inf].")  
  
        if len(bins) < 2:  
            raise ValueError("bins must contain at least 2 edges.")  
  
        parsed = []  
        for i, b in enumerate(bins):  
            try:  
                val = float(b)  
            except Exception:  
                raise TypeError(f"Bin edge at position {i} is not numeric: {repr(b)}")  
            if np.isnan(val):  
                raise ValueError(f"Bin edge at position {i} is NaN, which is not allowed.")  
            parsed.append(val)  
  
        for i in range(1, len(parsed)):  
            if parsed[i] <= parsed[i - 1]:  
                raise ValueError(  
                    f"bins must be strictly increasing. "  
                    f"Invalid at positions {i-1} and {i}: {parsed[i-1]} >= {parsed[i]}"  
                )  
  
        return parsed  
  
    # -----------------------------  
    # Row-level processing/validation  
    # -----------------------------  
    def _prepare_dataframe(self):  
        work = self.df[[self.entity_col, self.outcome_col, self.numerical_col]].copy()  
  
        # 1) Drop NaNs in required columns  
        before = len(work)  
        work = work.dropna(subset=[self.entity_col, self.outcome_col, self.numerical_col])  
        dropped = before - len(work)  
        if dropped > 0:  
            print(f"Warning: Dropped {dropped} row(s) with NaN in required columns.")  
  
        # 2) Validate entity is string  
        self._validate_entity_column(work)  
  
        # 3) Duplicate entity check (after NaN drop, as requested)  
        self._validate_no_duplicate_entityids(work)  
  
        # 4) Outcome coercion/validation  
        work[self.outcome_col] = self._coerce_outcome_series(work[self.outcome_col])  
  
        # 5) Numerical coercion/validation (allow numeric strings)  
        work[self.numerical_col] = self._coerce_numeric_series(work[self.numerical_col])  
  
        return work  
  
    def _validate_entity_column(self, df_):  
        invalid_mask = ~df_[self.entity_col].apply(lambda x: isinstance(x, str))  
        if invalid_mask.any():  
            bad = df_.loc[invalid_mask, self.entity_col]  
            examples = [  
                f"row={idx}, value={repr(val)}, type={type(val).__name__}"  
                for idx, val in bad.items()  
            ]  
            msg = "Entity IDs must be strings. Invalid rows:\n" + "\n".join(examples[:20])  
            if len(examples) > 20:  
                msg += f"\n... and {len(examples) - 20} more"  
            raise TypeError(msg)  
  
    def _validate_no_duplicate_entityids(self, df_):  
        dup_mask = df_.duplicated(subset=[self.entity_col], keep=False)  
        if dup_mask.any():  
            dups = df_.loc[dup_mask, [self.entity_col]]  
            lines = []  
            for ent, grp in dups.groupby(self.entity_col):  
                lines.append(f"entityid={repr(ent)}, rows={grp.index.tolist()}")  
            raise ValueError(  
                "Duplicate entity IDs found after dropping NaNs:\n" + "\n".join(lines)  
            )  
  
    @staticmethod  
    def _coerce_single_outcome(v):  
        # bool  
        if isinstance(v, (bool, np.bool_)):  
            return bool(v)  
  
        # ints/floats restricted to 0/1  
        if isinstance(v, (int, np.integer)):  
            if v in (0, 1):  
                return bool(v)  
            return np.nan  
  
        if isinstance(v, (float, np.floating)):  
            if v in (0.0, 1.0):  
                return bool(int(v))  
            return np.nan  
  
        # strings: "0","1","true","false" (any case)  
        if isinstance(v, str):  
            s = v.strip().lower()  
            if s in {"0", "1"}:  
                return s == "1"  
            if s in {"true", "false"}:  
                return s == "true"  
  
        return np.nan  
  
    def _coerce_outcome_series(self, s: pd.Series) -> pd.Series:  
        coerced = s.apply(self._coerce_single_outcome)  
        invalid_mask = pd.isna(coerced)  
        if invalid_mask.any():  
            bad = s[invalid_mask]  
            examples = [f"row={idx}, value={repr(val)}" for idx, val in bad.items()]  
            msg = (  
                "Outcome values must be one of: 0, 1, True, False, '0', '1', "  
                "'true'/'false' (any case). Invalid rows:\n"  
                + "\n".join(examples[:20])  
            )  
            if len(examples) > 20:  
                msg += f"\n... and {len(examples) - 20} more"  
            raise ValueError(msg)  
  
        return coerced.astype(bool)  
  
    def _coerce_numeric_series(self, s: pd.Series) -> pd.Series:  
        coerced = pd.to_numeric(s, errors="coerce")  
        invalid_mask = coerced.isna()  
        if invalid_mask.any():  
            bad = s[invalid_mask]  
            examples = [f"row={idx}, value={repr(val)}" for idx, val in bad.items()]  
            msg = (  
                "Numerical column contains non-numeric values that could not be coerced. "  
                "Invalid rows:\n" + "\n".join(examples[:20])  
            )  
            if len(examples) > 20:  
                msg += f"\n... and {len(examples) - 20} more"  
            raise ValueError(msg)  
  
        return coerced.astype(float)  
  
    # -----------------------------  
    # Core computation  
    # -----------------------------  
    def get_binned_summary(self) -> pd.DataFrame:  
        """  
        Returns DataFrame with columns:  
        - bin  
        - entity_count  
        - true_count  
        - risk_percentage  
        """  
        work = self.cleaned_df.copy()  
  
        work["_bin"] = pd.cut(  
            work[self.numerical_col],  
            bins=self.bins,  
            include_lowest=True,  
            right=True  
        )  
  
        outside_count = work["_bin"].isna().sum()  
        if outside_count > 0:  
            print(  
                f"Warning: {outside_count} row(s) fall outside provided bins "  
                f"and were excluded from summary."  
            )  
  
        work = work.dropna(subset=["_bin"])  
  
        summary = (  
            work.groupby("_bin", observed=False)  
            .agg(  
                entity_count=(self.entity_col, "count"),  
                true_count=(self.outcome_col, "sum"),  
            )  
            .reset_index()  
            .rename(columns={"_bin": "bin"})  
        )  
  
        # Skip bins below threshold (this also removes zero-count bins)  
        summary = summary[summary["entity_count"] >= self.minimum_count_per_bin].copy()  
  
        if summary.empty:  
            return pd.DataFrame(columns=["bin", "entity_count", "true_count", "risk_percentage"])  
  
        summary["risk_percentage"] = (summary["true_count"] / summary["entity_count"]) * 100.0  

        ci = summary.apply(  
            lambda r: self._wilson_ci(  
                k=int(r["true_count"]),  
                n=int(r["entity_count"]),  
                confidence_level=0.95  
            ),  
            axis=1  
        )  
        
        summary["ci_lower"] = ci.apply(lambda x: x[0])  
        summary["ci_upper"] = ci.apply(lambda x: x[1])  
        
        summary["ci_lower_pct"] = summary["ci_lower"] * 100  
        summary["ci_upper_pct"] = summary["ci_upper"] * 100  

        return summary  
  
  
    def _wilson_ci(self, k, n, confidence_level=0.95):  
        """  
        k: true_count  
        n: entity_count  
        returns (lower, upper) on [0, 1]  
        """  
        if n == 0:  
            return (np.nan, np.nan)  
    
        z = NormalDist().inv_cdf(0.5 + confidence_level / 2.0)  
        p = k / n  
    
        denom = 1 + (z**2 / n)  
        center = (p + (z**2 / (2 * n))) / denom  
        half = (z / denom) * np.sqrt((p * (1 - p) / n) + (z**2 / (4 * n**2)))  
    
        lo = max(0.0, center - half)  
        hi = min(1.0, center + half)  
        return lo, hi  

    # -----------------------------  
    # Plotting  
    # -----------------------------  
    def plot(  
        self,  
        filename: str = "plot_risk_across_numerical.jpg",  
        overall_from: str = "displayed",  # "displayed" or "all_cleaned"  
    ):  
        """  
        Plot risk percentage by numerical bin with 95% CI error bars and an overall reference line.  
    
        Parameters  
        ----------  
        filename : str  
            Output file path.  
        overall_from : str  
            - "displayed": overall % from bins shown in the plot (after filtering)  
            - "all_cleaned": overall % from all cleaned rows (before bin filtering)  
        """  
        summary = self.get_binned_summary()  
    
        if summary.empty:  
            print("No bins met minimum_count_per_bin. No plot created.")  
            return None  
    
        fig, ax = plt.subplots(figsize=(10, 6))  
    
        # X/Y values  
        x = np.arange(len(summary))  
        y = summary["risk_percentage"].to_numpy()  
    
        # Asymmetric CI error bars  
        yerr_lower = y - summary["ci_lower_pct"].to_numpy()  
        yerr_upper = summary["ci_upper_pct"].to_numpy() - y  
        yerr = np.vstack([yerr_lower, yerr_upper])  
    
        # Bars + CI  
        ax.bar(x, y, alpha=0.8, label="Bin risk %")  
        ax.errorbar(x, y, yerr=yerr, fmt="none", ecolor="black", capsize=4, linewidth=1)  
    
        # Overall horizontal reference line  
        if overall_from == "displayed":  
            overall_pct = (summary["true_count"].sum() / summary["entity_count"].sum()) * 100  
        elif overall_from == "all_cleaned":  
            overall_pct = self.cleaned_df[self.outcome_col].mean() * 100  
        else:  
            raise ValueError("overall_from must be 'displayed' or 'all_cleaned'.")  
    
        ax.axhline(  
            y=overall_pct,  
            color="red",  
            linestyle="--",  
            linewidth=2,  
            label=f"Overall = {overall_pct:.1f}%"  
        )  
    
        # Labels and formatting  
        ax.set_xticks(x)  
        ax.set_xticklabels(summary["bin"].astype(str), rotation=45, ha="right")  
        ax.set_xlabel(f"{self.numerical_col} bins")  
        ax.set_ylabel("Percentage with outcome")  
        ax.set_title(f"Percentage across {self.numerical_col}")  
        ax.set_ylim(0, 100)  
        ax.legend()  
    
        plt.tight_layout()  
        fig.savefig(filename, dpi=300, bbox_inches="tight")  
        print(f"Plot saved to: {filename}")  
        return fig, ax  