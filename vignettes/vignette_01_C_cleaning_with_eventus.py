# *** TO DO: Clean up the import
from eventus import EventSemantics, EventsCleanerConfig, EventsCleaner

sem    = EventSemantics.build_from_yaml("vignette_01_D_semantics.yaml")
config = EventsCleanerConfig.build_from_yaml("vignette_01_E_config_cleaner.yaml")

cleaner = EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()

cleaner.quality_report()