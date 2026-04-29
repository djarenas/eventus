import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Assume df is a clean DataFrame with admit_date and discharge_date
df["duration_days"] = (df["discharge_date"] - df["admit_date"]).dt.days

# Plot
fig, ax = plt.subplots(figsize=(10, 5))

ax.hist(
    df["duration_days"],
    bins=range(0, 181, 7),
    color="#028090",
    edgecolor="white",
    alpha=0.85,
)

# Percentile lines
for p, val in zip(
    [25, 50, 75, 90],
    np.percentile(df["duration_days"], [25, 50, 75, 90])
):
    ax.axvline(val, color="red", linestyle="--", linewidth=1)
    ax.text(val + 1, ax.get_ylim()[1] * 0.95, f"p{p}", fontsize=8, color="red")

ax.set_title("Distribution of Hospitalization Durations", fontsize=13)
ax.set_xlabel("Duration (days)", fontsize=11)
ax.set_ylabel("Number of hospitalizations", fontsize=11)
ax.set_xlim(0, 180)

plt.tight_layout()
plt.savefig("duration_histogram.png", dpi=150)
plt.close()
