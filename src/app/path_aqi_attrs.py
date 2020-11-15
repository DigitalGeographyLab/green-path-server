from typing import List, Set, Dict, Tuple, Optional
import utils.aq_exposures as aq_exps

class PathAqiAttrs:
    """Holds and manipulates all AQI related path attributes.
    """

    def __init__(self, aqi_exp_list: List[Tuple[float, float]]):
        self.aqi_exp_list = aqi_exp_list
        self.aqi_m: float = None
        self.aqc: float = None
        self.aqc_norm: float = None
        self.aqi_cl_exps: Dict[int, float] = None
        self.aqi_pcts: dict = None
        self.aqi_m_diff: float = None
        self.aqc_diff: float = None
        self.aqc_diff_rat: float = None
        self.aqc_diff_score: float = None

    def set_aqi_stats(self, length: float) -> None:
        self.aqi_m = aq_exps.get_mean_aqi(self.aqi_exp_list)
        self.aqc = aq_exps.get_total_aqi_cost_from_exps(self.aqi_exp_list)
        self.aqc_norm = round(self.aqc / length, 3)
        self.aqi_cl_exps = aq_exps.aggregate_aqi_class_exps(self.aqi_exp_list)
        self.aqi_pcts = aq_exps.get_aqi_class_pcts(self.aqi_cl_exps, length)

    def set_aqi_diff_attrs(self, s_path_aqi_attrs: 'PathAqiAttrs', len_diff: float) -> None:
        self.aqi_m_diff = round(self.aqi_m - s_path_aqi_attrs.aqi_m, 2)
        self.aqc_diff = round(self.aqc - s_path_aqi_attrs.aqc, 2)
        self.aqc_diff_rat = round((self.aqc_diff / s_path_aqi_attrs.aqc) * 100, 1) if s_path_aqi_attrs.aqc else 0
        self.aqc_diff_score = round(self.aqc_diff/len_diff * -1, 1) if len_diff else 0

    def get_aqi_props_dict(self) -> dict:
        return {
            'aqi_m': self.aqi_m,
            'aqc': round(self.aqc, 2),
            'aqc_norm': self.aqc_norm,
            'aqi_cl_exps': self.aqi_cl_exps,
            'aqi_pcts': self.aqi_pcts,
            'aqi_m_diff': self.aqi_m_diff,
            'aqc_diff': self.aqc_diff,
            'aqc_diff_rat': self.aqc_diff_rat,
            'aqc_diff_score': self.aqc_diff_score
        }
