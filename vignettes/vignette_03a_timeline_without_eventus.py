# Assumed: data is already cleaned — no nulls in patient_id, admit_date,
# or discharge_date, all dates are valid and parseable, no causality
# violations, no duplicates, no overlapping stays.
# These assumptions are silent — nothing in this script will tell you
# if they are violated.

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Inputs ────────────────────────────────────────────────────────────────
# hosp_df     : DataFrame with patient_id, admit_date, discharge_date
# patient_ids : list of all patient IDs (including non-hospitalised)

OBS_START = pd.Timestamp("2022-01-01")
OBS_END   = pd.Timestamp("2022-12-31")
OBS_DAYS  = (OBS_END - OBS_START).days

COLOR_EVENT   = "#4CAF50"
COLOR_BEFORE  = "#9E9E9E"
COLOR_MIDDLE  = "#F44336"
COLOR_AFTER   = "#BDBDBD"
COLOR_NOTHING = "#EEEEEE"

ROW_HEIGHT    = 0.5
BAR_HEIGHT    = 0.4
DPI           = 150
FIGSIZE_W     = 12

# ── Parse dates ───────────────────────────────────────────────────────────
hosp_df = hosp_df.copy()
hosp_df["admit_date"]     = pd.to_datetime(hosp_df["admit_date"])
hosp_df["discharge_date"] = pd.to_datetime(hosp_df["discharge_date"])

# ── Clip to observation period ────────────────────────────────────────────
hosp_df = hosp_df[
    (hosp_df["admit_date"]     <= OBS_END) &
    (hosp_df["discharge_date"] >= OBS_START)
].copy()
hosp_df["admit_date"]     = hosp_df["admit_date"].clip(lower=OBS_START)
hosp_df["discharge_date"] = hosp_df["discharge_date"].clip(upper=OBS_END)

# ── Compute active days per patient ───────────────────────────────────────
hosp_df["duration"] = (
    hosp_df["discharge_date"] - hosp_df["admit_date"]
).dt.days

active_days = (
    hosp_df.groupby("patient_id")["duration"]
    .sum()
    .reset_index()
    .rename(columns={"duration": "active_days"})
)

# ── Build full patient list including zero-hospitalization patients ────────
all_patients = pd.DataFrame({"patient_id": patient_ids})
all_patients = all_patients.merge(active_days, on="patient_id", how="left")
all_patients["active_days"] = all_patients["active_days"].fillna(0)

# ── Sort by active days descending ───────────────────────────────────────
all_patients = all_patients.sort_values(
    "active_days", ascending=False
).reset_index(drop=True)

# ── Build segments per patient ────────────────────────────────────────────
def get_segments(pid):
    stays = hosp_df[hosp_df["patient_id"] == pid].sort_values("admit_date")
    if stays.empty:
        return [(0, OBS_DAYS, COLOR_NOTHING)]

    segments      = []
    prev_end_days = 0
    is_first      = True

    for _, row in stays.iterrows():
        left  = (row["admit_date"]     - OBS_START).days
        right = (row["discharge_date"] - OBS_START).days
        width = right - left

        if left > prev_end_days:
            gap_color = COLOR_BEFORE if is_first else COLOR_MIDDLE
            segments.append((prev_end_days, left - prev_end_days, gap_color))

        if width > 0:
            segments.append((left, width, COLOR_EVENT))

        prev_end_days = max(prev_end_days, right)
        is_first = False

    if prev_end_days < OBS_DAYS:
        segments.append((prev_end_days, OBS_DAYS - prev_end_days, COLOR_AFTER))

    return segments

# ── Plot ──────────────────────────────────────────────────────────────────
n_patients = len(all_patients)
fig_h      = max(2.0, n_patients * ROW_HEIGHT + 1.5)
fig, ax    = plt.subplots(figsize=(FIGSIZE_W, fig_h))

for i, row in all_patients.iterrows():
    segments = get_segments(row["patient_id"])
    for left, width, color in segments:
        if width > 0:
            ax.broken_barh(
                [(left, width)],
                (i - BAR_HEIGHT / 2, BAR_HEIGHT),
                facecolors=color,
            )

# ── Axes ──────────────────────────────────────────────────────────────────
ax.set_xlim(0, OBS_DAYS)
ax.set_ylim(-0.5, n_patients - 0.5)
ax.invert_yaxis()
ax.set_yticks([])
ax.set_xlabel("Day of observation period", fontsize=10)
ax.set_title("Hospitalization Timeline — 2022", fontsize=12)

# ── X axis ticks ─────────────────────────────────────────────────────────
tick_offsets = range(0, OBS_DAYS, 30)
tick_labels  = [
    (OBS_START + pd.Timedelta(days=d)).strftime("%b") for d in tick_offsets
]
ax.set_xticks(list(tick_offsets))
ax.set_xticklabels(tick_labels, fontsize=9, rotation=45, ha="right")

# ── Legend ────────────────────────────────────────────────────────────────
handles = [
    mpatches.Patch(facecolor=COLOR_EVENT,   label="Hospitalized"),
    mpatches.Patch(facecolor=COLOR_BEFORE,  label="Inactive before first stay"),
    mpatches.Patch(facecolor=COLOR_MIDDLE,  label="Inactive between stays"),
    mpatches.Patch(facecolor=COLOR_AFTER,   label="Inactive after last stay"),
    mpatches.Patch(facecolor=COLOR_NOTHING, label="No hospitalizations"),
]
ax.legend(
    handles         = handles,
    fontsize        = 9,
    loc             = "upper left",
    bbox_to_anchor  = (1.01, 1),
    borderaxespad   = 0,
    frameon         = True,
)

fig.tight_layout()
fig.savefig("timeline_2022.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)
