import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# ── Assumed: coverage_df is already clean, demographics_df has DOBs ───────

# ── Step 1 — Build age window (65 to 70) per patient ─────────────────────
demographics_df["date_of_birth"] = pd.to_datetime(demographics_df["date_of_birth"])

def add_years(dt, years):
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, day=28)

demographics_df["obs_start"] = demographics_df["date_of_birth"].apply(
    lambda d: add_years(d, 65)
)
demographics_df["obs_end"] = demographics_df["date_of_birth"].apply(
    lambda d: add_years(d, 70)
)

# ── Step 2 — Clip coverage to obs window ──────────────────────────────────
coverage_df["admit_date"]     = pd.to_datetime(coverage_df["admit_date"])
coverage_df["discharge_date"] = pd.to_datetime(coverage_df["discharge_date"])

coverage_df = coverage_df.merge(
    demographics_df[["patient_id", "obs_start", "obs_end"]],
    on="patient_id", how="inner"
)
coverage_df = coverage_df[
    (coverage_df["admit_date"]     < coverage_df["obs_end"]) &
    (coverage_df["discharge_date"] > coverage_df["obs_start"])
].copy()
coverage_df["admit_date"]     = coverage_df[["admit_date",     "obs_start"]].max(axis=1)
coverage_df["discharge_date"] = coverage_df[["discharge_date", "obs_end"]].min(axis=1)
coverage_df["duration"] = (
    coverage_df["discharge_date"] - coverage_df["admit_date"]
).dt.days

# ── Step 3 — Compute active days per patient ──────────────────────────────
active = (
    coverage_df.groupby("patient_id")["duration"]
    .sum().reset_index().rename(columns={"duration": "active_days"})
)
obs_days = demographics_df.copy()
obs_days["span_days"] = (obs_days["obs_end"] - obs_days["obs_start"]).dt.days
all_patients = obs_days.merge(active, on="patient_id", how="left")
all_patients["active_days"]   = all_patients["active_days"].fillna(0)
all_patients["inactive_days"] = all_patients["span_days"] - all_patients["active_days"]

# ── Step 4 — Compute before/after/middle per patient ─────────────────────
sorted_cov = coverage_df.sort_values(["patient_id", "admit_date"])
first_start = sorted_cov.groupby("patient_id")["admit_date"].first()
last_end    = sorted_cov.groupby("patient_id")["discharge_date"].last()

all_patients = all_patients.set_index("patient_id")
obs_start_map = demographics_df.set_index("patient_id")["obs_start"]
obs_end_map   = demographics_df.set_index("patient_id")["obs_end"]

all_patients["before"] = (
    first_start - obs_start_map
).dt.days.clip(lower=0)
all_patients["after"] = (
    obs_end_map - last_end
).dt.days.clip(lower=0)
all_patients["middle"] = (
    all_patients["inactive_days"] -
    all_patients["before"].fillna(0) -
    all_patients["after"].fillna(0)
).clip(lower=0)
all_patients = all_patients.reset_index()
n_total = len(all_patients)

# ── Step 5 — Sample and plot stacked timeline ─────────────────────────────
sample = all_patients.sample(n=50, random_state=42)
# ... (stacked timeline plotting — ~80 lines, omitted for brevity)

# ── Step 6 — Build violin data arrays ────────────────────────────────────
has_coverage  = all_patients["active_days"] > 0
has_before    = all_patients["before"]  > 0
has_after     = all_patients["after"]   > 0

cov_counts = coverage_df.groupby("patient_id").size()
has_middle = all_patients["patient_id"].isin(
    cov_counts[cov_counts >= 2].index
) & (all_patients["middle"] > 0)

arrays = {
    "active_days":   all_patients["active_days"].values,
    "inactive_days": all_patients["inactive_days"].values,
}
breakdown = {
    "inactive_days":  all_patients.loc[all_patients["inactive_days"] > 0, "inactive_days"].values,
    "before":         all_patients.loc[has_before, "before"].values,
    "after":          all_patients.loc[has_after,  "after"].values,
    "middle":         all_patients.loc[has_middle, "middle"].values,
}

# ── Step 7 — Plot total violin ────────────────────────────────────────────
def plot_violin_group(arrays_dict, title, path):
    keys   = list(arrays_dict.keys())
    ns     = [len(v) for v in arrays_dict.values()]
    max_n  = max(ns)
    widths = [0.8 * n / max_n for n in ns]

    fig, ax = plt.subplots(figsize=[12, 7])
    for i, (key, values) in enumerate(arrays_dict.items()):
        if len(np.unique(values)) < 2:
            continue
        kde    = gaussian_kde(values.astype(np.float64))
        y_grid = np.linspace(values.min(), values.max(), 200)
        dens   = kde(y_grid)
        scaled = dens / dens.max() * widths[i] / 2
        ax.fill_betweenx(y_grid, i - scaled, i + scaled, alpha=0.75)
        ax.plot(i - scaled, y_grid, linewidth=0.8)
        ax.plot(i + scaled, y_grid, linewidth=0.8)
        q25, q50, q75 = np.percentile(values, [25, 50, 75])
        ax.hlines([q25, q50, q75], i - widths[i]/2, i + widths[i]/2,
                  colors="#333333", linewidth=1.2, linestyle="--")
        n   = len(values)
        pct = 100 * n / n_total
        ax.text(i, ax.get_ylim()[0] - 5, f"{key}\n(n={n:,}, {pct:.1f}%)",
                ha="center", fontsize=9)

    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([""] * len(keys))
    ax.set_title(title, fontsize=12)
    ax.set_ylabel("Days", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

plot_violin_group(arrays,    "Active vs Inactive — Age 65-70", "total.png")
plot_violin_group(breakdown, "Coverage gap breakdown",          "breakdown.png")
