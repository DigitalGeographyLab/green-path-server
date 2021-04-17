from dataclasses import dataclass
from typing import List
import gp_server.app.noise_exposures as noise_exps


@dataclass
class PathNoiseAttrs:
    """Holds all noise exposure related path attributes.
    """
    noises: dict
    mdB: float
    nei: float
    nei_norm: float
    noise_range_exps: dict
    noise_pcts: dict
    mdB_diff: float = None
    nei_diff: float = None
    nei_diff_rat: float = None

    def set_noise_diff_attrs(self, s_path_noise_attrs):
        self.mdB_diff = round(self.mdB - s_path_noise_attrs.mdB, 1)
        self.nei_diff = round(self.nei - s_path_noise_attrs.nei, 1)
        self.nei_diff_rat = round((
            self.nei_diff / s_path_noise_attrs.nei
        ) * 100, 1) if s_path_noise_attrs.nei > 0 else 0

    def get_noise_props_dict(self) -> dict:
        return {
            'noises': self.noises,
            'mdB': self.mdB,
            'nei': self.nei,
            'nei_norm': round(self.nei_norm, 2),
            'noise_range_exps': self.noise_range_exps,
            'noise_pcts': self.noise_pcts,
            'mdB_diff':  self.mdB_diff,
            'nei_diff':  self.nei_diff,
            'nei_diff_rat': self.nei_diff_rat
        }


def create_path_noise_attrs(
    noises_list: List[dict],
    db_costs: dict,
    length: float
) -> PathNoiseAttrs:

    noises = noise_exps.aggregate_exposures(noises_list)
    nei = round(noise_exps.get_noise_cost(noises, db_costs), 1)
    max_db_cost = max(db_costs.values())
    noise_range_exps = noise_exps.get_noise_range_exps(noises, length)

    return PathNoiseAttrs(
        noises=noises,
        mdB=noise_exps.get_mean_noise_level(noises, length),
        nei=nei,
        nei_norm=round(nei / (max_db_cost * length), 4),
        noise_range_exps=noise_range_exps,
        noise_pcts=noise_exps.get_noise_range_pcts(noise_range_exps, length)
    )
