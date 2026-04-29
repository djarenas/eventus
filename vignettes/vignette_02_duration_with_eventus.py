# events object already built from Vignette 1.
# If it exists, it is structurally sound — guaranteed by the constructor.

from eventus import EventsDurationPlotter, HistogramConfig

# ── Unstratified ──────────────────────────────────────────────────────────
config  = HistogramConfig.build_from_yaml("hist_config.yaml")
plotter = EventsDurationPlotter(events)
plotter.plot_histogram(config=config, path="duration.png")

# ── Stratified — same config, one extra line ──────────────────────────────
plotter = EventsDurationPlotter(events, stratify_by="hospital_id")
plotter.plot_histogram(config=config, path="duration_by_hospital.png")
