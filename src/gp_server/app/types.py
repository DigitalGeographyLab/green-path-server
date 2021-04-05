from dataclasses import dataclass, field
from typing import Dict, Union, List, Tuple
import gp_server.app.noise_exposures as noise_exps
import common.geometry as geom_utils
from gp_server.app.constants import RoutingMode


@dataclass
class PathEdge:
    """Class for handling edge attributes during routing."""
    id: int
    length: float
    bike_time_cost: float
    aqi: Union[float, None]
    aqi_cl: Union[float, None]
    noises: Union[dict, None]
    gvi: Union[float, None]
    gvi_cl: Union[int, None]
    coords: List[Tuple[float]]
    coords_wgs: List[Tuple[float]]
    mdB: float = field(init=False)
    db_range: int = field(init=False)

    def __post_init__(self):
        self.mdB = noise_exps.get_mean_noise_level(self.noises, self.length) if self.noises else 0
        self.db_range = noise_exps.get_noise_range(self.mdB)

    def as_props(self) -> dict:
        """Returns length (m), AQI, GVI, mean dB and WGS coordinates of the edge as a dictionary.
        """
        return {
            'length': self.length,
            'aqi': self.aqi,
            'gvi': self.gvi,
            'mdB': self.mdB,
            'coords_wgs': geom_utils.round_coordinates(self.coords_wgs)
        }


edge_group_attr_by_routing_mode: Dict[RoutingMode, str] = {
    RoutingMode.QUIET: 'db_range',
    RoutingMode.GREEN: 'gvi_cl',
    RoutingMode.CLEAN: 'aqi_cl',
    RoutingMode.FAST: 'gvi_cl',
    RoutingMode.SAFE: 'gvi_cl',
}
