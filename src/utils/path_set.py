from typing import List, Set, Dict, Tuple
import time
import utils.paths_overlay_filter as path_overlay_filter
import utils.utils as utils
from utils.path import Path
import utils.geometry as geom_utils
from utils.logger import Logger

class PathSet:
    """An instance of PathSet holds, manipulates and filters both shortest and least cost paths.
    """

    def __init__(self, logger: Logger, set_type: str):
        self.log = logger
        self.set_type: str = set_type # either 'quiet' or 'clean'
        self.shortest_path: Path = None
        self.green_paths: List[Path] = []

    def set_shortest_path(self, s_path: Path) -> None:
        self.shortest_path = s_path

    def add_green_path(self, q_path: Path) -> None:
        self.green_paths.append(q_path)

    def get_all_paths(self) -> List[Path]: return [self.shortest_path] + self.green_paths

    def get_green_path_count(self) -> int: return len(self.green_paths)

    def set_path_edges(self, G) -> None:
        """Loads edges for all paths in the set from a graph (based on node lists of the paths).
        """
        if (self.shortest_path is not None):
            self.shortest_path.set_path_edges(G)
        if (len(self.green_paths) > 0):
            for gp in self.green_paths:
                gp.set_path_edges(G)

    def aggregate_path_attrs(self) -> None:
        """Aggregates edge level path attributes to paths.
        """
        if (self.shortest_path is not None):
            self.shortest_path.aggregate_path_attrs(geom=True, noises=True, aqi=True)
        if (len(self.green_paths) > 0):
            for gp in self.green_paths:
                gp.aggregate_path_attrs(geom=True, noises=True, aqi=True)

    def filter_out_unique_len_paths(self) -> None:
        self.log.debug('green path count: '+ str(len(self.green_paths)))
        filtered = []
        prev_len = self.shortest_path.length
        for path in self.green_paths:
            if (path.length != prev_len):
                filtered.append(path)
            prev_len = path.length
        self.green_paths = filtered
        self.log.debug('green path count after filter by unique length: '+ str(len(self.green_paths)))

    def filter_out_unique_geom_paths(self, buffer_m=50) -> None:
        """Filters out short / green paths with nearly similar geometries (using "greenest" wins policy when paths overlap).
        """
        cost_attr = 'aqc_norm' if (self.set_type == 'clean') else 'nei_norm'
        unique_paths_names = path_overlay_filter.get_unique_paths_by_geom_overlay(self.log, self.get_all_paths(), buffer_m=buffer_m, cost_attr=cost_attr)
        if (unique_paths_names is not None):
            self.filter_paths_by_names(unique_paths_names)

    def filter_paths_by_names(self, filter_names: List[str]) -> None:
        """Filters out short / green paths by list of path names to keep.
        """
        filtered_green_paths = [path for path in self.green_paths if path.name in filter_names]
        if ('short_p' not in filter_names):
            self.log.debug('replacing shortest path with shortest green path')
            shortest_green_path = filtered_green_paths[0]
            shortest_green_path.set_path_type('short')
            shortest_green_path.set_path_name('short_p')
            self.set_shortest_path(shortest_green_path)
            filtered_green_paths = filtered_green_paths[1:]
        self.green_paths = filtered_green_paths

    def set_path_exp_attrs(self, db_costs) -> None:
        self.shortest_path.set_noise_attrs(db_costs)
        self.shortest_path.set_aqi_attrs()
        for path in self.green_paths:
            path.set_noise_attrs(db_costs)
            path.set_aqi_attrs()

    def set_green_path_diff_attrs(self) -> None:
        for path in self.green_paths:
            path.set_green_path_diff_attrs(self.shortest_path)

    def get_paths_as_feature_collection(self) -> List[dict]:
        feats = [path.get_as_geojson_feature() for path in [self.shortest_path] + self.green_paths]
        return geom_utils.as_geojson_feature_collection(feats)

    def get_edges_as_feature_collection(self) -> dict:
        if (self.set_type == 'clean'):
            edge_group_attr = 'aqi_cl'
        else:
            edge_group_attr = 'dBrange'
        
        for path in [self.shortest_path] + self.green_paths:
            path.aggregate_edge_groups_by_attr(edge_group_attr)
        
        feat_lists = [path.get_edge_groups_as_features() for path in [self.shortest_path] + self.green_paths]

        feats = [feat for feat_list in feat_lists for feat in feat_list]
        return geom_utils.as_geojson_feature_collection(feats)
