# from __future__ import annotations  
  
# from dataclasses import dataclass  
# from typing import ClassVar  
  
# from .shared import GeneralConfig, _PlotterConfigBase  
# from histogram_plot_config import HistogramPlotConfig  
  
  
# @dataclass  
# class SurvivalCurveConfig:  
#     # Keep/replace with your existing fields  
#     enabled: bool = True  
#     ci_alpha: float = 0.2  
#     linewidth: float = 2.0  
  
  
# @dataclass  
# class FacetConfig:  
#     # Keep/replace with your existing fields  
#     enabled: bool = False  
#     by: str = "none"  
#     ncols: int = 2  
  
  
# @dataclass  
# class OccurrenceResultTimingConfig(_PlotterConfigBase):  
#     _PREFIX: ClassVar[str] = "OccurrenceResultTimingConfig"  
#     _SECTION_MAP: ClassVar[dict[str, type]] = {  
#         "general": GeneralConfig,  
#         "histogram": HistogramPlotConfig,  
#         "survival_curve": SurvivalCurveConfig,  
#         "facet": FacetConfig,  
#     }  
  
#     general: GeneralConfig = GeneralConfig()  
#     histogram: HistogramPlotConfig = HistogramPlotConfig()  
#     survival_curve: SurvivalCurveConfig = SurvivalCurveConfig()  
#     facet: FacetConfig = FacetConfig()  
  