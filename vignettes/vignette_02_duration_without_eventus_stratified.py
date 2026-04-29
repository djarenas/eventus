import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Assume df is a clean DataFrame with admit_date, discharge_date, hospital_id
df["duration_days"] = (df["discharge_date"] - df["admit_date"]).dt.days

strata    = df["hospital_id"].unique()
colors    = ["#028090", "#F45B69", "#6B4226", "#A8C686", "#7B2D8B",
             "#E07B39", "#2E4057", "#048A81", "#54C6EB", "#EF946C"]
bin_edges = range(0, 181, 7)
percentiles_to_show = [25, 50, 75, 90]

fig, axes = plt.subplots(
    nrows=len(strata),
    ncols=1,
    figsize=(10, 4 * len(strata)),
    sharex=True,
)

if len(strata) == 1:
    axes = [axes]

for i, (stratum, ax) in enumerate(zip(strata, axes)):
    subset = df[df["hospital_id"] == stratum]["duration_days"]
    color  = colors[i % len(colors)]

    ax.hist(
        subset,
        bins=bin_edges,
        color=color,
        edgecolor="white",
        alpha=0.85,
    )

    for p, val in zip(
        percentiles_to_show,
        np.percentile(subset, percentiles_to_show)
    ):
        ax.axvline(val, color="red", linestyle="--", linewidth=1)
        ax.text(val + 1, ax.get_ylim()[1] * 0.95, f"p{p}", fontsize=8, color="red")

    ax.set_title(f"Hospital: {stratum}", fontsize=12)
    ax.set_ylabel("Number of hospitalizations", fontsize=10)
    ax.set_xlim(0, 180)

axes[-1].set_xlabel("Duration (days)", fontsize=11)
fig.suptitle("Distribution of Hospitalization Durations by Hospital", fontsize=14)

plt.tight_layout()
plt.savefig("duration_histogram_stratified.png", dpi=150)
plt.close()
