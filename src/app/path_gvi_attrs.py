from dataclasses import dataclass
from typing import List, Dict, Tuple
import utils.greenery_exposures as gvi_exps


@dataclass
class PathGviAttrs:
    """Holds and manipulates all GVI related path attributes.
    """
    gvi_m: float
    gvi_cl_exps: Dict[int, float]
    gvi_cl_pcts: dict
    gvi_m_diff: float = None

    def set_gvi_diff_attrs(self, s_path_gvi_attrs: 'PathGviAttrs') -> None:
        self.gvi_m_diff = round(self.gvi_m - s_path_gvi_attrs.gvi_m, 2)

    def get_gvi_props_dict(self) -> dict:
        return {
            'gvi_m': self.gvi_m,
            'gvi_cl_exps': self.gvi_cl_exps,
            'gvi_cl_pcts': self.gvi_cl_pcts,
            'gvi_m_diff': self.gvi_m_diff
        }


def create_gvi_attrs(gvi_exp_list: List[Tuple[float, float]]) -> PathGviAttrs:

    gvi_cl_exps = gvi_exps.aggregate_gvi_class_exps(gvi_exp_list)

    return PathGviAttrs(
        gvi_m = gvi_exps.get_mean_gvi(gvi_exp_list),
        gvi_cl_exps = gvi_cl_exps,
        gvi_cl_pcts = gvi_exps.get_gvi_class_pcts(gvi_cl_exps)
    )
