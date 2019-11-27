from typing import List, Set, Dict, Tuple, Optional
import utils.noise_exposures as noise_exps

class PathNoiseAttrs:
    """Holds and manipulates all noise exposure related path attributes.
    """

    def __init__(self, path_type: str, noises_list: dict):
        self.path_type: str = path_type
        self.noises: dict = noise_exps.aggregate_exposures(noises_list)
        self.mdB: float = None
        self.nei: float = None
        self.nei_norm: float = None
        self.noise_pcts: dict = None
        self.noises_diff: dict = None
        self.mdB_diff: float = None
        self.nei_diff: float = None
        self.nei_diff_rat: float = None
        self.nei_diff_score: float = None

    def set_noise_attrs(self, db_costs: dict, length: float) -> None:
        if (self.noises is not None):
            self.mdB = noise_exps.get_mean_noise_level(self.noises, length)
            self.nei = round(noise_exps.get_noise_cost(noises=self.noises, db_costs=db_costs), 1)
            self.nei_norm = round(self.nei / (0.6 * length), 4)
            self.noise_pcts = noise_exps.get_noise_range_pcts(self.noises, length)

    def set_noise_diff_attrs(self, s_path_noise_attrs, len_diff=0) -> None:
        self.noises_diff = noise_exps.get_noises_diff(s_path_noise_attrs.noises, self.noises)
        self.mdB_diff = round(self.mdB - s_path_noise_attrs.mdB, 1)
        self.nei_diff = round(self.nei - s_path_noise_attrs.nei, 1)
        self.nei_diff_rat = round((self.nei_diff / s_path_noise_attrs.nei) * 100, 1) if s_path_noise_attrs.nei > 0 else 0
        self.nei_diff_score = round(self.nei_diff/len_diff * -1, 1) if len_diff > 0 else 0

    def get_noise_props_dict(self) -> dict:
        return {
            'noises': self.noises,
            'mdB': self.mdB,
            'nei': self.nei,
            'nei_norm': round(self.nei_norm, 2),
            'noise_pcts': self.noise_pcts,
            'noises_diff': self.noises_diff,
            'mdB_diff':  self.mdB_diff,
            'nei_diff':  self.nei_diff,
            'nei_diff_rat': self.nei_diff_rat,
            'path_score': self.nei_diff_score
            }
