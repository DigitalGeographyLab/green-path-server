from dataclasses import dataclass, field
from typing import Dict, Union, List, Tuple
import utils.noise_exposures as noise_exps
import utils.geometry as geom_utils
from app.constants import RoutingMode


@dataclass
class PathEdge:
    """Class for handling edge attributes during routing."""
    id: int
    length: float
    length_b: float
    aqi: Union[float, None]
    aqi_cl: Union[float, None]
    noises: Union[dict, None]
    gvi: Union[float, None]
    gvi_cl: Union[int, None]
    coords: List[Tuple[float]]
    coords_wgs: List[Tuple[float]]
    db_range: int = field(init=False)

    def __post_init__(self):
        mean_db = noise_exps.get_mean_noise_level(self.noises, self.length) if self.noises else 0
        self.db_range = noise_exps.get_noise_range(mean_db)

    def as_props(self) -> dict:
        """Used in research mode only (?).
        """
        return {
            'id': self.id,
            'length': self.length,
            'aqi': self.aqi,
            'noises': self.noises,
            'gvi': self.gvi,
            'gvi_cl': self.gvi_cl,
            'coords': geom_utils.round_coordinates(self.coords),
            'coords_wgs': geom_utils.round_coordinates(self.coords_wgs)
        }


edge_group_attr_by_routing_mode: Dict[RoutingMode, str] = {
    RoutingMode.CLEAN: 'aqi_cl',
    RoutingMode.QUIET: 'db_range',
    RoutingMode.GREEN: 'gvi_cl'
}
