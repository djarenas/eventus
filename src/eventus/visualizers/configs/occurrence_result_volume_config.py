# from __future__ import annotations  
  
# from dataclasses import dataclass  
# from typing import ClassVar  
  
# from .shared import GeneralConfig, _PlotterConfigBase  
# from histogram_plot_config import HistogramPlotConfig  
  
  
# @dataclass  
# class VolumeBarConfig:  
#     # Keep/replace with your existing fields  
#     enabled: bool = True  
#     alpha: float = 0.9  
#     edgecolor: str = "#FFFFFF"  
#     linewidth: float = 0.5  
  
  
# @dataclass  
# class OccurrenceResultVolumeConfig(_PlotterConfigBase):  
#     _PREFIX: ClassVar[str] = "OccurrenceResultVolumeConfig"  
#     _SECTION_MAP: ClassVar[dict[str, type]] = {  
#         "general": GeneralConfig,  
#         "histogram": HistogramPlotConfig,  
#         "volume_bar": VolumeBarConfig,  
#     }  
  
#     general: GeneralConfig = GeneralConfig()  
#     histogram: HistogramPlotConfig = HistogramPlotConfig()  
#     volume_bar: VolumeBarConfig = VolumeBarConfig()  