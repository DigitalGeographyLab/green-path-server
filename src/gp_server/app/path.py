from shapely.geometry import LineString
from typing import List, Tuple
import gp_server.env as env
import gp_server.utils.geometry as geom_utils
from gp_server.app.logger import Logger
from gp_server.app.types import PathEdge
from gp_server.app.path_noise_attrs import PathNoiseAttrs, create_path_noise_attrs
from gp_server.app.path_aqi_attrs import PathAqiAttrs, create_aqi_attrs
from gp_server.app.path_gvi_attrs import PathGviAttrs, create_gvi_attrs
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.constants import PathType


class Path:
    """An instance of Path holds all attributes of a path and provides methods for manipulating them.
    """

    def __init__(self, orig_node: int, edge_ids: List[int], name: str, path_type, cost_coeff: float=0.0):
        self.orig_node: int = orig_node
        self.edge_ids: List[int] = edge_ids
        self.edges: List[PathEdge] = []
        self.edge_groups: List[Tuple[int, List[dict]]] = []
        self.name: str = name
        self.path_type: PathType = path_type
        self.cost_coeff: float = cost_coeff
        self.geometry = None
        self.length: float = None
        self.len_diff: float = 0
        self.len_diff_rat: float = None
        self.missing_aqi: bool = False
        self.missing_noises: bool = False
        self.missing_gvi: bool = False
        self.noise_attrs: PathNoiseAttrs = None
        self.aqi_attrs: PathAqiAttrs = None
        self.gvi_attrs: PathGviAttrs = None
    
    def set_path_name(self, path_name: str): self.name = path_name

    def set_path_type(self, path_type: str): self.path_type = path_type

    def set_path_edges(self, G: GraphHandler) -> None:
        """Iterates through the path's node list and loads the respective edges (& their attributes) from a graph.
        """
        self.edges = G.get_path_edges_by_ids(self.edge_ids)

    def aggregate_path_attrs(self, log: Logger) -> None:
        """Aggregates path attributes form list of edges.
        """
        path_coords = [coord for edge in self.edges for coord in edge.coords]
        self.geometry = LineString(path_coords)
        self.length = round(sum(edge.length for edge in self.edges), 2)
        self.length_b = round(sum(edge.length_b for edge in self.edges), 2)
        self.missing_noises = True if (None in [edge.noises for edge in self.edges]) else False
        self.missing_aqi = True if (None in [edge.aqi for edge in self.edges]) else False
        self.missing_gvi = True if (None in [edge.gvi for edge in self.edges]) else False
        if self.missing_gvi:
            log.warning(f'Found missing GVI values for path ({[edge.gvi for edge in self.edges]})')

    def set_noise_attrs(self, db_costs: dict) -> None:
        if not self.missing_noises:
            noises_list = [edge.noises for edge in self.edges]
            self.noise_attrs = create_path_noise_attrs(
                noises_list = noises_list, 
                db_costs = db_costs, 
                length = self.length
            )

    def set_aqi_attrs(self) -> None:
        if not self.missing_aqi:
            aqi_exp_list = [(edge.aqi, edge.length) for edge in self.edges]
            self.aqi_attrs = create_aqi_attrs(aqi_exp_list, self.length)

    def set_gvi_attrs(self) -> None:
        if not self.missing_gvi:
            gvi_exp_list = [(edge.gvi, edge.length) for edge in self.edges]
            self.gvi_attrs = create_gvi_attrs(gvi_exp_list)

    def set_green_path_diff_attrs(self, shortest_path: 'Path') -> None:
        self.len_diff = round(self.length - shortest_path.length, 1)
        self.len_diff_rat = round((self.len_diff / shortest_path.length) * 100, 1) if shortest_path.length > 0 else 0
        if self.noise_attrs and shortest_path.noise_attrs:
            self.noise_attrs.set_noise_diff_attrs(shortest_path.noise_attrs, len_diff=self.len_diff)
        if self.aqi_attrs and shortest_path.aqi_attrs:
            self.aqi_attrs.set_aqi_diff_attrs(shortest_path.aqi_attrs, len_diff=self.len_diff)
        if self.gvi_attrs and shortest_path.gvi_attrs:
            self.gvi_attrs.set_gvi_diff_attrs(shortest_path.gvi_attrs)
    
    def aggregate_edge_groups_by_attr(self, grouping_attr: str) -> None:
        """Create groups of edges by PathEdge attribute values. Groups are formed by
        aggregating all adjacent edges with same attribute value (grouping_attr). 
        """

        cur_group = []
        cur_group_id: int = 0
        for edge in self.edges:
            # get either aqi class or noise range value
            value = getattr(edge, grouping_attr)
            # add edge to current or new group based on group_attr
            if value == cur_group_id:
                cur_group.append(edge)
            else:
                # before creating a new group, add the current group to self.edge_groups
                if cur_group:
                    self.edge_groups.append((cur_group_id, cur_group))
                # create new edge group and add edge there
                cur_group = []
                cur_group_id = value
                cur_group.append(edge)
        self.edge_groups.append((cur_group_id, cur_group))

    def get_edge_groups_as_features(self) -> List[dict]:
        features = []
        for group in self.edge_groups:
            group_coords = [coords for edge in group[1] for coords in edge.coords_wgs]
            group_coords = geom_utils.round_coordinates(group_coords, digits=6)       
            feature = self.__get_geojson_feature_dict(group_coords)
            feature['properties'] = { 'value': group[0], 'path': self.name, 'p_len_diff': self.len_diff, 'p_length': self.length }
            features.append(feature)
        return features

    def get_as_geojson_feature(self) -> dict:
        wgs_coords = [coord for edge in self.edges for coord in edge.coords_wgs]
        wgs_coords = geom_utils.round_coordinates(wgs_coords, digits=6)

        feature_d = self.__get_geojson_feature_dict(wgs_coords)

        props = {
            'type': self.path_type.value,
            'id': self.name,
            'length': self.length,
            'length_b': self.length_b,
            'len_diff': self.len_diff,
            'len_diff_rat': self.len_diff_rat,
            'cost_coeff': self.cost_coeff,
            'missing_aqi': self.missing_aqi,
            'missing_noises': self.missing_noises,
            'missing_gvi': self.missing_gvi,
        }
        noise_props = self.noise_attrs.get_noise_props_dict() if self.noise_attrs else {}
        aqi_props = self.aqi_attrs.get_aqi_props_dict() if self.aqi_attrs else {}
        gvi_props = self.gvi_attrs.get_gvi_props_dict() if self.gvi_attrs else {}

        research_props = {
            'edge_ids': self.edge_ids,
            'edge_first_props': self.edges[0].as_props(),
            'edge_last_props': self.edges[len(self.edges)-1].as_props(),
        } if env.research_mode else {}

        feature_d['properties'] = { 
            **props, 
            **noise_props, 
            **aqi_props,
            **gvi_props,
            **research_props 
        }
        return feature_d

    def __get_geojson_feature_dict(self, coords: List[tuple]) -> dict:
        """Returns a dictionary with GeoJSON schema and geometry based on the given geometry. The returned dictionary can be used as a
        feature inside a GeoJSON feature collection. 
        """
        feature = { 
            'type': 'Feature', 
            'properties': {}, 
            'geometry': {
                'coordinates': coords,
                'type': 'LineString'
            }
        }
        return feature
