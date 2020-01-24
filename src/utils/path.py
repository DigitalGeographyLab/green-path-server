from shapely.geometry import Point, LineString
from typing import List, Set, Dict, Tuple, Optional
import utils.graphs as graph_utils
import utils.geometry as geom_utils
from utils.path_noises import PathNoiseAttrs
from utils.path_aqi_attrs import PathAqiAttrs
from utils.graph_handler import GraphHandler

class Path:
    """An instance of Path holds all attributes of a path and provides methods for manipulating them.
    """

    def __init__(self, orig_node: int, edge_ids: List[int], name: str, path_type: str, cost_coeff: float = 0.0):
        self.orig_node: int = orig_node
        self.edge_ids: List[int] = edge_ids
        self.edges: List[dict] = []
        self.edge_groups: List[Tuple[int, List[dict]]] = []
        self.name: str = name
        self.path_type: str = path_type
        self.cost_coeff: float = cost_coeff
        self.geometry = None
        self.length: float = None
        self.len_diff: float = 0
        self.len_diff_rat: float = None
        self.noise_attrs: PathNoiseAttrs = None
        self.aqi_attrs: PathAqiAttrs = None
    
    def set_path_name(self, path_name: str): self.name = path_name

    def set_path_type(self, path_type: str): self.path_type = path_type

    def set_path_edges(self, G: GraphHandler, orig_point: Point) -> None:
        """Iterates through the path's node list and loads the respective edges (& their attributes) from a graph.
        """
        self.edges = G.get_edges_from_edge_ids(self.edge_ids, orig_point)

    def aggregate_path_attrs(self, geom: bool = True, length: bool = True, noises: bool = True, aqi: bool = False) -> None:
        """Aggregates path attributes form list of edges.
        """
        path_coords = [coord for edge in self.edges for coord in edge['coords']] if (geom == True) else None
        self.geometry = LineString(path_coords) if (geom == True) else self.geometry
        self.length = round(sum(edge['length'] for edge in self.edges ), 2) if (length == True) else self.length
        if (noises == True):
            noises_list = [edge['noises'] for edge in self.edges]
            self.noise_attrs = PathNoiseAttrs(self.path_type, noises_list)
        if (aqi == True):
            aqi_exp_list = [edge['aqi_exp'] for edge in self.edges if edge['aqi_exp'] is not None]
            if (len(aqi_exp_list) > 0):
                self.aqi_attrs = PathAqiAttrs(self.path_type, aqi_exp_list)

    def set_noise_attrs(self, db_costs: dict) -> None:
        if (self.noise_attrs is not None):
            self.noise_attrs.set_noise_attrs(db_costs, self.length)

    def set_aqi_attrs(self) -> None:
        if (self.aqi_attrs is not None):
            self.aqi_attrs.set_aqi_stats(self.length)

    def set_green_path_diff_attrs(self, shortest_path: 'Path') -> None:
        self.len_diff = round(self.length - shortest_path.length, 1)
        self.len_diff_rat = round((self.len_diff / shortest_path.length) * 100, 1) if shortest_path.length > 0 else 0
        if (self.noise_attrs is not None and shortest_path.noise_attrs is not None):
            self.noise_attrs.set_noise_diff_attrs(shortest_path.noise_attrs, len_diff=self.len_diff)
        if (self.aqi_attrs is not None and shortest_path.aqi_attrs is not None):
            self.aqi_attrs.set_aqi_diff_attrs(shortest_path.aqi_attrs, len_diff=self.len_diff)
    
    def aggregate_edge_groups_by_attr(self, group_attr: str) -> None:
        cur_group = []
        cur_group_id: int = 0
        for edge in self.edges:
            # add edge to current or new group based on group_attr
            if (edge[group_attr] == cur_group_id):
                cur_group.append(edge)
            else:
                # before creating a new group, add the current group to self.edge_groups
                if (cur_group != []): self.edge_groups.append((cur_group_id, cur_group))
                # create new edge group and add edge there
                cur_group = []
                cur_group_id = edge[group_attr]
                cur_group.append(edge)
        self.edge_groups.append((cur_group_id, cur_group))

    def get_edge_groups_as_features(self) -> List[dict]:
        features = []
        for group in self.edge_groups:
            group_coords = [coord for edge in group[1] for coord in edge['coords_wgs']]
            group_coords = geom_utils.round_coordinates(group_coords, digits=6)       
            feature = geom_utils.as_geojson_feature(group_coords)
            feature['properties'] = { 'value': group[0], 'path': self.name, 'p_len_diff': self.len_diff, 'p_length': self.length }
            features.append(feature)
        return features

    def get_as_geojson_feature(self) -> dict:
        wgs_coords = [coord for edge in self.edges for coord in edge['coords_wgs']]
        wgs_coords = geom_utils.round_coordinates(wgs_coords, digits=6)

        feature_d = geom_utils.as_geojson_feature(wgs_coords)

        props = {
            'type' : self.path_type,
            'id' : self.name,
            'length' : self.length,
            'len_diff' : self.len_diff,
            'len_diff_rat' : self.len_diff_rat,
            'cost_coeff' : self.cost_coeff
        }
        noise_props = self.noise_attrs.get_noise_props_dict() if self.noise_attrs is not None else {}
        aqi_props = self.aqi_attrs.get_aqi_props_dict() if self.aqi_attrs is not None else {}
        feature_d['properties'] = { **props, **noise_props, **aqi_props }
        return feature_d
