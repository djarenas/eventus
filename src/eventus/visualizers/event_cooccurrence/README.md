# eventus.visualizers.event_cooccurrence

KDE plotters for co-occurrence analysis results. Both plotters consume
a statistical test intermediate and produce a publication-ready figure
comparing observed vs permutation null distributions.

---

## Plotters

### `EventCoOccurrenceGapPlotter`

Two-panel KDE figure comparing observed vs null gap distributions.

```python
from eventus.visualizers.event_cooccurrence import EventCoOccurrenceGapPlotter
from eventus.visualizers.configs import EventCoOccurrenceGapPlotConfig

plotter = EventCoOccurrenceGapPlotter(gap_test)
plotter.plot("gap_distributions.png")
```

Top panel: A → nearest B. Bottom panel: B → nearest A. Each panel
shows the KDE of observed per-entity median gaps vs the pooled
permutation null, with median lines annotated.

---

### `EventCoOccurrenceDirectionalityPlotter`

Single-panel KDE figure centered at zero.

```python
from eventus.visualizers.event_cooccurrence import EventCoOccurrenceDirectionalityPlotter
from eventus.visualizers.configs import EventCoOccurrenceDirectionalityPlotConfig

plotter = EventCoOccurrenceDirectionalityPlotter(dir_test)
plotter.plot("directionality.png")
```

Positive x = A tends to precede B. Negative x = B tends to precede A.
Shows observed vs null signed gap distributions with mean lines annotated.

---

Both plotters accept an optional config object. Defaults produce
publication-ready figures. See
`src/eventus/visualizers/configs/event_co_occurrence_gap_plot_config.py`
and `event_co_occurrence_directionality_plot_config.py` for all options.
