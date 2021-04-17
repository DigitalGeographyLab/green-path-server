from enum import Enum
from typing import Dict, Union, List, Tuple
from dataclasses import dataclass, field
import common.geometry as geom_utils
import gp_server.app.noise_exposures as noise_exps
from shapely.geometry import Point
from common.igraph import Edge as E
from gp_server.app.constants import RoutingMode, TravelMode


@dataclass
class PathEdge:
    """Class for handling edge attributes during routing."""
    id: int
    length: float
    bike_time_cost: float
    bike_safety_cost: float
    allows_biking: bool
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
    RoutingMode.SAFE: 'gvi_cl'
}


class Bikeability(Enum):
    NO_BIKE_STAIRS = 1
    NO_BIKE = 2
    BIKE_OK_STAIRS = 3
    BIKE_OK = 4


@dataclass(frozen=True)
class RoutingConf:
    aq_sens: List[float]
    gvi_sens: List[float]
    noise_sens: List[float]
    db_costs: Dict[int, float]
    sensitivities_by_routing_mode: Dict[RoutingMode, List[float]]
    fastest_path_cost_attr_by_travel_mode: Dict[TravelMode, E]


@dataclass(frozen=True)
class OdSettings:
    orig_point: Point
    dest_point: Point
    travel_mode: TravelMode
    routing_mode: RoutingMode
    sensitivities: Union[List[float], None]


@dataclass
class NearestEdge:
    attrs: dict
    distance: float


@dataclass
class LinkToEdgeSpec:
    edge: dict
    snap_point: Point


@dataclass
class OdNodeData:
    id: int
    is_temp_node: bool
    link_to_edge_spec: Union[LinkToEdgeSpec, None] = None


@dataclass(frozen=True)
class OdData:
    orig_node: OdNodeData
    dest_node: OdNodeData
    orig_link_edges: Union[Tuple[dict], Tuple[()]]
    dest_link_edges: Union[Tuple[dict], Tuple[()]]
