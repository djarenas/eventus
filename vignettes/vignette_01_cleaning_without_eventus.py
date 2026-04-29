import pandas as pd

# Load data
df = pd.read_csv("hospitalizations.csv")

# Drop rows with null patient_id, admit_date, or discharge_date
df = df[df["patient_id"].notna()]
df = df[df["admit_date"].notna()]
df = df[df["discharge_date"].notna()]

# Parse dates
df["admit_date"] = pd.to_datetime(df["admit_date"], errors="coerce")
df["discharge_date"] = pd.to_datetime(df["discharge_date"], errors="coerce")

# Drop rows where dates could not be parsed
df = df[df["admit_date"].notna()]
df = df[df["discharge_date"].notna()]

# Drop implausible dates
df = df[df["admit_date"] >= "1920-01-01"]
df = df[df["admit_date"] <= "2100-01-01"]
df = df[df["discharge_date"] >= "1920-01-01"]
df = df[df["discharge_date"] <= "2100-01-01"]

# Enforce causality — drop rows where admit date is after discharge date
df = df[df["admit_date"] <= df["discharge_date"]]

# Drop exact duplicates
df = df.drop_duplicates(subset=["patient_id", "admit_date", "discharge_date"])

# Sort
df = df.sort_values(["patient_id", "admit_date"]).reset_index(drop=True)

# Merge overlapping stays (gap = 0 days)
def merge_overlapping(group):
    merged = []
    current_start = group.iloc[0]["admit_date"]
    current_end   = group.iloc[0]["discharge_date"]
    for _, row in group.iloc[1:].iterrows():
        if row["admit_date"] <= current_end:
            current_end = max(current_end, row["discharge_date"])
        else:
            merged.append({
                "patient_id":       group.name,
                "admit_date":       current_start,
                "discharge_date":   current_end,
            })
            current_start = row["admit_date"]
            current_end   = row["discharge_date"]
    merged.append({
        "patient_id":       group.name,
        "admit_date":       current_start,
        "discharge_date":   current_end,
    })
    return pd.DataFrame(merged)

df = (
    df.groupby("patient_id", group_keys=False)
      .apply(merge_overlapping)
      .reset_index(drop=True)
)
