from dataclasses import dataclass, field
from typing import Union, List, Tuple
import utils.noise_exposures as noise_exps
import utils.geometry as geom_utils


@dataclass
class PathEdge:
    """Class for handling edge attributes during routing."""
    id: int
    length: float
    length_b: float
    aqi: Union[float, None]
    aqi_cl: Union[float, None]
    noises: Union[dict, None]
    coords: List[Tuple[float]]
    coords_wgs: List[Tuple[float]]
    db_range: int = field(init=False)

    def __post_init__(self):
        mean_db = noise_exps.get_mean_noise_level(self.noises, self.length) if self.noises else 0
        self.db_range = noise_exps.get_noise_range(mean_db)

    def as_props(self) -> dict:
        return {
            'id': self.id,
            'length': self.length,
            'aqi': self.aqi,
            'noises': self.noises,
            'coords': geom_utils.round_coordinates(self.coords),
            'coords_wgs': geom_utils.round_coordinates(self.coords_wgs)
        }
