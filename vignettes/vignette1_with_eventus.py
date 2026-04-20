from eventus import EventSemantics, EventsCleanerConfig, EventsCleaner

sem    = EventSemantics.build_from_yaml("hosp_semantics.yaml")
config = EventsCleanerConfig.build_from_yaml("hosp_cleaner_config.yaml")

cleaner = EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()

cleaner.quality_report()