from typing import List, Set, Dict, Tuple, Optional
import utils.aq_exposures as aq_exps

class PathAqiAttrs:
    """Holds and manipulates all AQI related path attributes.
    """

    def __init__(self, path_type: str, aqi_exp_list: List[Tuple[float, float]]):
        self.path_type: str = path_type
        self.aqi_exp_list = aqi_exp_list
        self.m_aqi: float = None
        self.aqc: float = None
        self.aqc_norm: float = None
        self.aqi_pcts: dict = None
        self.m_aqi_diff: float = None
        self.aqc_diff: float = None
        self.aqc_diff_rat: float = None
        self.aqc_diff_score: float = None

    def set_aqi_stats(self, length: float) -> None:
        self.m_aqi = aq_exps.get_mean_aqi(self.aqi_exp_list)
        self.aqc = aq_exps.get_total_aqi_cost_from_exps(self.aqi_exp_list)
        self.aqc_norm = round(self.aqc / length, 3)
        aqi_class_exps = aq_exps.aggregate_aqi_class_exps(self.aqi_exp_list)
        self.aqi_pcts = aq_exps.get_aqi_class_pcts(aqi_class_exps, length)

    def set_aqi_diff_attrs(self, s_path_aqi_attrs: 'PathAqiAttrs', len_diff: float) -> None:
        self.m_aqi_diff = round(self.m_aqi - s_path_aqi_attrs.m_aqi, 2)
        self.aqc_diff = round(self.aqc - s_path_aqi_attrs.aqc, 2)
        self.aqc_diff_rat = round((self.aqc_diff / s_path_aqi_attrs.aqc) * 100, 1) if s_path_aqi_attrs.aqc > 0 else 0
        self.aqc_diff_score = round((self.aqc_diff/len_diff) * -1, 1) if len_diff > 0 else 0
