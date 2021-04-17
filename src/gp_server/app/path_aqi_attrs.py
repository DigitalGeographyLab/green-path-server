from dataclasses import dataclass
from typing import List, Dict, Tuple
import gp_server.app.aq_exposures as aq_exps


@dataclass
class PathAqiAttrs:
    """Holds and manipulates all AQI related path attributes.
    """
    aqi_m: float
    aqc: float
    aqc_norm: float
    aqi_cl_exps: Dict[int, float]
    aqi_cl_pcts: dict
    aqi_m_diff: float = None
    aqc_diff: float = None
    aqc_diff_rat: float = None

    def set_aqi_diff_attrs(self, s_path_aqi_attrs: 'PathAqiAttrs') -> None:
        self.aqi_m_diff = round(self.aqi_m - s_path_aqi_attrs.aqi_m, 2)
        self.aqc_diff = round(self.aqc - s_path_aqi_attrs.aqc, 2)
        self.aqc_diff_rat = round((
            self.aqc_diff / s_path_aqi_attrs.aqc) * 100, 1
        ) if s_path_aqi_attrs.aqc else 0

    def get_aqi_props_dict(self) -> dict:
        return {
            'aqi_m': self.aqi_m,
            'aqc': round(self.aqc, 2),
            'aqc_norm': self.aqc_norm,
            'aqi_cl_exps': self.aqi_cl_exps,
            'aqi_cl_pcts': self.aqi_cl_pcts,
            'aqi_m_diff': self.aqi_m_diff,
            'aqc_diff': self.aqc_diff,
            'aqc_diff_rat': self.aqc_diff_rat
        }


def create_aqi_attrs(
    aqi_exp_list: List[Tuple[float, float]],
    length: float
) -> PathAqiAttrs:

    aqc = aq_exps.get_total_aqi_cost_from_exps(aqi_exp_list)
    aqi_cl_exps = aq_exps.aggregate_aqi_class_exps(aqi_exp_list)

    return PathAqiAttrs(
        aqi_m=aq_exps.get_mean_aqi(aqi_exp_list),
        aqc=aqc,
        aqc_norm=round(aqc / length, 3),
        aqi_cl_exps=aqi_cl_exps,
        aqi_cl_pcts=aq_exps.get_aqi_class_pcts(aqi_cl_exps, length),
    )
