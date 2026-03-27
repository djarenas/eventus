"""
viz_helpers.py
Visualization helpers for SpanCoverageResult.
Each function takes a results DataFrame + options and saves to path.
Supports .html, .png, .jpg, .jpeg output formats.
Config is loaded from viz_config.yaml in the same directory.
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import yaml

_ERROR_PREFIX = "[viz_helpers] Error"

# --------------------------------------------------------------------------- #
# Load config once at import time
# --------------------------------------------------------------------------- #

_CONFIG_PATH = pathlib.Path(__file__).parent / "viz_config.yaml"

def _load_config() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

_CFG = _load_config()


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _ext(path: str) -> str:
    return pathlib.Path(path).suffix.lower()


def _assert_path(path: str) -> None:
    ext = _ext(path)
    if ext not in {".html", ".png", ".jpg", ".jpeg"}:
        raise ValueError(
            f"{_ERROR_PREFIX}: unsupported file extension '{ext}'. "
            "Use .html, .png, .jpg, or .jpeg"
        )


def _save_fig(fig: plt.Figure, path: str) -> None:
    dpi = _CFG["general"]["dpi"]
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def _save_html(html: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {path}")


def _apply_style() -> None:
    try:
        plt.style.use(_CFG["general"]["style"])
    except Exception:
        pass


def _parse_intervals(row: pd.Series, span: float) -> list[tuple[float, float, str]]:
    """
    Parse event_starts / event_ends into a list of (left, width, color) segments
    covering the full span, interleaving active (green) and gap (red) segments,
    with before (gray) at the start and after (gray) at the end.

    Returns list of (left_days, width_days, color) tuples in order.
    """
    cfg = _CFG["stacked_bar"]["colors"]

    if pd.isna(row.get("active_days")):
        return [(0, span, cfg["no_coverage"])]

    before = float(row["inactive_days_before_first_event"] or 0)
    after  = float(row["inactive_days_after_last_event"]   or 0)

    span_start = pd.Timestamp(row["span_start"]).normalize()

    starts_raw = str(row["event_starts"]).split(" | ")
    ends_raw   = str(row["event_ends"]).split(" | ")

    starts = [(pd.Timestamp(s).normalize() - span_start).days for s in starts_raw]
    ends   = [(pd.Timestamp(e).normalize() - span_start).days for e in ends_raw]

    segments = []

    if before > 0:
        segments.append((0, before, cfg["before"]))

    for i, (s, e) in enumerate(zip(starts, ends)):
        w = e - s
        if w > 0:
            segments.append((s, w, cfg["active"]))
        if i < len(starts) - 1:
            gap_start = e
            gap_end   = starts[i + 1]
            gap_w     = gap_end - gap_start
            if gap_w > 0:
                segments.append((gap_start, gap_w, cfg["middle"]))

    last_end = ends[-1]
    if after > 0:
        segments.append((last_end, after, cfg["after"]))

    return segments


# --------------------------------------------------------------------------- #
# 1. Stacked bar (per entity)
# --------------------------------------------------------------------------- #

def plot_stacked_bar(
    results_df: pd.DataFrame,
    path: str,
    entity_col: str,
    n_sample: int | None = None,
    random_state: int | None = None,
) -> None:
    """
    Per-entity stacked bar chart sorted by active_days asc,
    then inactive_days_before_first_event asc.
    Supports .html, .png, .jpg, .jpeg output.
    """
    _assert_path(path)

    df = results_df.copy()
    if n_sample is not None and n_sample < len(df):
        df = df.sample(n=n_sample, random_state=random_state).reset_index(drop=True)

    df = df.sort_values(
        ["active_days", "inactive_days_before_first_event"],
        ascending=[True, True],
        na_position="first",
    ).reset_index(drop=True)

    ext = _ext(path)
    if ext == ".html":
        _save_html(_stacked_bar_html(df, entity_col, n_sample, len(results_df), random_state), path)
    else:
        _save_fig(_stacked_bar_fig(df, entity_col), path)


def _stacked_bar_fig(df: pd.DataFrame, entity_col: str) -> plt.Figure:
    cfg      = _CFG["stacked_bar"]["colors"]
    fs       = _CFG["general"]["font_size"]
    title_fs = _CFG["general"]["title_font_size"]
    _apply_style()

    n     = len(df)
    fig_h = max(4, n * 0.18)
    fig, ax = plt.subplots(figsize=(12, fig_h))

    for i, (_, row) in enumerate(df.iterrows()):
        span     = float(row["span_duration_days"]) if not pd.isna(row["span_duration_days"]) else 0
        segments = _parse_intervals(row, span)
        for left, width, color in segments:
            if width > 0:
                ax.barh(i, width, left=left, color=color, height=0.7)

    ax.set_xlabel("Days", fontsize=fs)
    ax.set_ylabel(f"{entity_col} (sorted by active days)", fontsize=fs)
    ax.set_title(f"Coverage per {entity_col} within span", fontsize=title_fs)
    ax.tick_params(axis="y", which="both", left=False, labelleft=False)
    ax.tick_params(axis="x", labelsize=fs - 1)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=cfg["before"],      label="Inactive before first event"),
        Patch(facecolor=cfg["active"],      label="Active"),
        Patch(facecolor=cfg["middle"],      label="Gaps (middle inactive)"),
        Patch(facecolor=cfg["after"],       label="Inactive after last event"),
        Patch(facecolor=cfg["no_coverage"], label="No coverage"),
    ]
    ax.legend(handles=legend_elements, loc="upper center",
              bbox_to_anchor=(0.5, 1.1), ncol=3,
              fontsize=fs - 1, frameon=False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.08)
    return fig


def _stacked_bar_html(
    df: pd.DataFrame,
    entity_col: str,
    n_sample: int | None,
    n_total: int,
    random_state: int | None,
) -> str:
    cfg  = _CFG["stacked_bar"]
    bh   = cfg["bar_height"]
    gap  = cfg["gap"]
    cols = cfg["colors"]

    rows = []
    for _, r in df.iterrows():
        span     = float(r["span_duration_days"]) if not pd.isna(r["span_duration_days"]) else 0
        segments = _parse_intervals(r, span)
        rows.append({"span": span, "segments": [
            {"left": left, "width": width, "color": color}
            for left, width, color in segments
        ]})

    n_shown  = len(rows)
    sampled  = n_sample is not None and n_sample < n_total
    subtitle = (
        f"Sampled {n_shown} of {n_total} entities (random_state={random_state}). "
        if sampled else f"{n_shown} entities. "
    )
    subtitle += "Sorted by active days asc, then entry date asc."

    data_json = json.dumps(rows)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; background:#fff; color:#333; margin:0; padding:16px; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:14px; font-size:12px; color:#666; }}
  .ld {{ display:flex; align-items:center; gap:5px; }}
  .lb {{ width:10px; height:10px; border-radius:2px; flex-shrink:0; }}
  .bar-wrap {{ display:flex; align-items:center; gap:8px; margin-bottom:{gap}px; }}
  .bar-track {{ flex:1; height:{bh}px; position:relative; background:#f0f0f0; border-radius:3px; overflow:hidden; }}
  .seg {{ position:absolute; top:0; height:100%; transition:opacity .15s; cursor:default; }}
  .seg:hover {{ opacity:0.75; }}
  .subtitle {{ font-size:11px; color:#999; margin-top:8px; text-align:right; }}
</style></head><body>
<div class="legend">
  <div class="ld"><div class="lb" style="background:{cols['before']}"></div>Inactive before first event</div>
  <div class="ld"><div class="lb" style="background:{cols['active']}"></div>Active</div>
  <div class="ld"><div class="lb" style="background:{cols['middle']}"></div>Gaps (middle inactive)</div>
  <div class="ld"><div class="lb" style="background:{cols['after']}"></div>Inactive after last event</div>
  <div class="ld"><div class="lb" style="background:{cols['no_coverage']}"></div>No coverage</div>
</div>
<div id="chart"></div>
<div class="subtitle">{subtitle}</div>
<script>
const data = {data_json};
const el = document.getElementById('chart');
data.forEach(row => {{
  const wrap = document.createElement('div'); wrap.className = 'bar-wrap';
  const track = document.createElement('div'); track.className = 'bar-track';
  row.segments.forEach(s => {{
    if (s.width <= 0) return;
    const seg = document.createElement('div'); seg.className = 'seg';
    seg.style.left    = ((s.left  / row.span) * 100).toFixed(3) + '%';
    seg.style.width   = ((s.width / row.span) * 100).toFixed(3) + '%';
    seg.style.background = s.color;
    seg.title = `${{Math.round(s.width)}}d`;
    track.appendChild(seg);
  }});
  wrap.appendChild(track);
  el.appendChild(wrap);
}});
</script></body></html>"""


# --------------------------------------------------------------------------- #
# 2. Active timeseries
# --------------------------------------------------------------------------- #

def plot_active_timeseries(results_df: pd.DataFrame, path: str, entity_col: str) -> None:
    _assert_path(path)

    df = results_df.copy()
    span_max = int(df["span_duration_days"].max())
    tick_interval = _CFG["active_timeseries"]["tick_interval_days"]

    days = np.arange(0, span_max + 1)

    # Denominator: count entities active on each day using broadcasting
    span_durations = df["span_duration_days"].to_numpy().reshape(-1, 1)
    denom_mask = days <= span_durations
    denominators = denom_mask.sum(axis=0)

    # Numerator: count entities active on each day
    pct_active = np.zeros_like(days, dtype=float)

    active_mask = ~pd.isna(df.get("active_days"))
    df_active = df[active_mask]

    for span_start, starts_raw, ends_raw in zip(
        df_active["span_start"],
        df_active["event_starts"],
        df_active["event_ends"]
    ):
        span_start_ts = pd.Timestamp(span_start)
        start_days = [(pd.Timestamp(s) - span_start_ts).days
                      for s in str(starts_raw).split(" | ")]
        end_days = [(pd.Timestamp(e) - span_start_ts).days
                    for e in str(ends_raw).split(" | ")]
        for s, e in zip(start_days, end_days):
            pct_active[s:e] += 1

    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(denominators > 0, 100 * pct_active / denominators, np.nan)

    ext = _ext(path)
    if ext == ".html":
        _save_html(_timeseries_html(days, pct, tick_interval, entity_col), path)
    else:
        _save_fig(_timeseries_fig(days, pct, tick_interval, entity_col), path)


def _timeseries_fig(
    days: np.ndarray,
    pct: np.ndarray,
    tick_interval: int,
    entity_col: str,
) -> plt.Figure:
    cfg      = _CFG["active_timeseries"]
    fs       = _CFG["general"]["font_size"]
    title_fs = _CFG["general"]["title_font_size"]
    _apply_style()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    valid = ~np.isnan(pct)
    ax.fill_between(days[valid], pct[valid], alpha=cfg["fill_alpha"], color=cfg["line_color"])
    ax.plot(days[valid], pct[valid], color=cfg["line_color"], linewidth=1.5)

    ax.set_xlabel("Days since span start", fontsize=fs)
    ax.set_ylabel(f"% of {entity_col}s active", fontsize=fs)
    ax.set_title(f"Active {entity_col}s over relative time", fontsize=title_fs)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(tick_interval))
    ax.tick_params(labelsize=fs - 1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    fig.tight_layout()
    return fig


def _timeseries_html(
    days: np.ndarray,
    pct: np.ndarray,
    tick_interval: int,
    entity_col: str,
) -> str:
    cfg   = _CFG["active_timeseries"]
    valid = ~np.isnan(pct)
    pts   = [{"x": int(d), "y": round(float(p), 1)}
             for d, p, v in zip(days, pct, valid) if v]
    ticks = list(range(0, int(days[-1]) + 1, tick_interval))
    color = cfg["line_color"]

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
</head><body>
<div style="position:relative;width:100%;height:400px;">
  <canvas id="c"></canvas>
</div>
<script>
const pts = {json.dumps(pts)};
new Chart(document.getElementById('c'), {{
  type: 'line',
  data: {{
    labels: pts.map(p => p.x),
    datasets: [{{
      data: pts.map(p => p.y),
      borderColor: '{color}',
      backgroundColor: '{color}22',
      fill: true,
      pointRadius: 0,
      borderWidth: 1.5,
      tension: 0.1,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{
        ticks: {{
          callback: (val, i) => {{
            const ticks = {json.dumps(ticks)};
            return ticks.includes(pts[i]?.x) ? pts[i].x : '';
          }},
          maxRotation: 0,
        }},
        title: {{ display: true, text: 'Days since span start' }}
      }},
      y: {{
        min: 0, max: 105,
        ticks: {{ callback: v => v + '%' }},
        title: {{ display: true, text: '% of {entity_col}s active' }}
      }}
    }}
  }}
}});
</script></body></html>"""


# --------------------------------------------------------------------------- #
# 3. Coverage histogram
# --------------------------------------------------------------------------- #

def plot_coverage_histogram(
    results_df: pd.DataFrame,
    path: str,
    entity_col: str,
) -> None:
    """
    Distribution of active_days across all entities.
    Zero-coverage entities (NA) are included as 0.
    Supports .png, .jpg, .jpeg, .html output.
    """
    _assert_path(path)

    active = results_df["active_days"].fillna(0).astype(float)

    ext = _ext(path)
    if ext == ".html":
        _save_html(_histogram_html(active), path)
    else:
        _save_fig(_histogram_fig(active, entity_col), path)


def _histogram_fig(active: pd.Series, entity_col: str) -> plt.Figure:
    cfg      = _CFG["coverage_histogram"]
    fs       = _CFG["general"]["font_size"]
    title_fs = _CFG["general"]["title_font_size"]
    _apply_style()

    fig, ax   = plt.subplots(figsize=cfg["figsize"])
    zero_mask = active == 0
    nonzero   = active[~zero_mask]
    n_zero    = zero_mask.sum()
    total     = len(active)

    if len(nonzero) > 0:
        counts, bins, _ = ax.hist(
            nonzero, bins=cfg["bins"], color=cfg["color"],
            edgecolor="white", linewidth=0.5, label="Has coverage"
        )
        perc = counts / total * 100
        ax.clear()
        ax.bar(bins[:-1], perc, width=np.diff(bins), align="edge",
               color=cfg["color"], edgecolor="white", linewidth=0.5,
               label="Has coverage")
    else:
        perc = []

    if n_zero > 0:
        bin_w = (nonzero.max() / cfg["bins"]) if len(nonzero) > 0 else 10
        ax.bar(0, (n_zero / total) * 100, width=bin_w,
               color=cfg["zero_coverage_color"], edgecolor="white", linewidth=0.5,
               label=f"No coverage ({n_zero} entities)")

    ax.set_xlabel("Active days", fontsize=fs)
    ax.set_ylabel(f"% of {entity_col}", fontsize=fs)
    ax.set_title(f"Distribution of active days per {entity_col}", fontsize=title_fs)
    ax.tick_params(labelsize=fs - 1)
    if n_zero > 0 or len(perc) > 0:
        ax.legend(fontsize=fs - 1)
    fig.tight_layout()
    return fig


def _histogram_html(active: pd.Series) -> str:
    cfg   = _CFG["coverage_histogram"]
    color = cfg["color"]
    bins  = cfg["bins"]

    counts, edges = np.histogram(active, bins=bins)
    total    = counts.sum()
    percents = (counts / total * 100).tolist()
    labels   = [f"{int(edges[i])}-{int(edges[i+1])}" for i in range(len(edges) - 1)]
    colors   = [
        cfg["zero_coverage_color"] if edges[i] == 0 and edges[i+1] <= 1 else color
        for i in range(len(edges) - 1)
    ]

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
</head><body>
<div style="position:relative;width:100%;height:400px;">
  <canvas id="c"></canvas>
</div>
<script>
new Chart(document.getElementById('c'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(labels)},
    datasets: [{{
      data: {json.dumps(percents)},
      backgroundColor: {json.dumps(colors)},
      borderColor: '#fff',
      borderWidth: 0.5,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{
        title: {{ display: true, text: 'Active days' }},
        ticks: {{ maxRotation: 45 }}
      }},
      y: {{
        title: {{ display: true, text: 'Percentage of entities (%)' }}
      }}
    }}
  }}
}});
</script></body></html>"""