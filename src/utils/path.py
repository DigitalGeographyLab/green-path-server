from shapely.geometry import Point, LineString
from typing import List, Set, Dict, Tuple, Optional
import utils.graphs as graph_utils
import utils.geometry as geom_utils
from utils.path_noises import PathNoiseAttrs

class Path:
    """An instance of Path contains all path specific attributes and methods for manipulating them.
    """

    def __init__(self, nodes: List[int], name: str, path_type: str, cost_attr: str, cost_coeff: float = 0.0):
        self.nodes: List[int] = nodes
        self.edges: List[dict] = []
        self.cost_update_time = None
        self.name: str = name
        self.path_type: str = path_type
        self.set_type: str = None
        self.cost_attr: str = cost_attr
        self.cost_coeff: float = cost_coeff
        self.geometry = None
        self.length: float = None
        self.len_diff: float = 0
        self.len_diff_rat: float = None
        self.noise_attrs: PathNoiseAttrs = None
    
    def set_path_name(self, path_name: str): self.name = path_name

    def set_path_type(self, path_type: str): self.path_type = path_type

    def set_set_type(self, set_type: str): self.set_type = set_type

    def set_path_edges(self, graph):
        """Iterates through the path's node list and loads the respective edges (& their attributes) from a graph.
        """
        self.edges = graph_utils.get_edges_from_nodelist(graph, self.nodes, self.cost_attr)

    def aggregate_path_attrs(self, geom=True, length=True, noises=False):
        """Aggregates path attributes form list of edges.
        """
        path_coords = [coord for edge in self.edges for coord in edge['coords']] if (geom == True) else None
        self.geometry = LineString(path_coords) if (geom == True) else self.geometry
        self.length = round(sum(edge['length'] for edge in self.edges ), 2) if (length == True) else self.length
        self.cost_update_time = self.edges[0]['cost_update_time'] if ('cost_update_time' in self.edges[0]) else self.cost_update_time
        if (noises == True):
            noises_list = [edge['noises'] for edge in self.edges]
            self.noise_attrs = PathNoiseAttrs(self.path_type, noises_list)

    def set_noise_attrs(self, db_costs: dict):
        self.noise_attrs.set_noise_attrs(db_costs, self.length)
    
    def set_green_path_diff_attrs(self, shortest_path):
        self.len_diff = round(self.length - shortest_path.length, 1)
        self.len_diff_rat = round((self.len_diff / shortest_path.length) * 100, 1) if shortest_path.length > 0 else 0
        if (self.path_type == 'quiet'):
            self.noise_attrs.set_noise_diff_attrs(shortest_path.noise_attrs, len_diff=self.len_diff)

    def get_as_geojson_feature(self) -> dict:
        props = {
            'type' : self.path_type,
            'id' : self.name,
            'length' : self.length,
            'len_diff' : self.len_diff,
            'len_diff_rat' : self.len_diff_rat,
            'cost_coeff' : self.cost_coeff
        }
        # TODO add aqi exposure props here
        exposure_props = self.noise_attrs.get_noise_props_dict() if self.set_type == 'quiet' else {}
        feature_d = geom_utils.get_geojson_feature_from_geom(self.geometry, from_epsg=3879)
        feature_d['properties'] = { **props, **exposure_props }
        return feature_d
