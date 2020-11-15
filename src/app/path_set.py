from typing import List, Set, Dict, Tuple
import utils.paths_overlay_filter as path_overlay_filter
from app.constants import RoutingMode, PathType
from app.logger import Logger
from app.path import Path

class PathSet:
    """An instance of PathSet holds, manipulates and filters both shortest and least cost paths.
    """

    def __init__(self, logger: Logger, routing_mode: RoutingMode):
        self.log = logger
        self.routing_mode = routing_mode
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
        if self.shortest_path:
            self.shortest_path.set_path_edges(G)
        if self.green_paths:
            for gp in self.green_paths:
                gp.set_path_edges(G)

    def aggregate_path_attrs(self) -> None:
        """Aggregates edge level path attributes to paths.
        """
        if self.shortest_path:
            self.shortest_path.aggregate_path_attrs()
        if self.green_paths:
            for gp in self.green_paths:
                gp.aggregate_path_attrs()
    
    def filter_out_green_paths_missing_exp_data(self) -> None:
        path_count = len(self.green_paths)
        if self.routing_mode == RoutingMode.CLEAN:
            self.green_paths = [path for path in self.green_paths if not path.missing_aqi]
        if self.routing_mode == RoutingMode.QUIET:
            self.green_paths = [path for path in self.green_paths if not path.missing_noises]
        filtered_out_count = path_count - len(self.green_paths)
        if filtered_out_count:
            self.log.info('Filtered out '+ str(filtered_out_count) + ' green paths without exposure data')

    def filter_out_unique_edge_sequence_paths(self) -> None:
        self.log.debug('Green path count: '+ str(len(self.green_paths)))
        filtered = []
        prev_edges = self.shortest_path.edge_ids
        for path in self.green_paths:
            if (path.edge_ids != prev_edges):
                filtered.append(path)
            prev_edges = path.edge_ids
        self.green_paths = filtered
        self.log.debug('Green path count after filter by unique edge sequence: '+ str(len(self.green_paths)))

    def filter_out_unique_geom_paths(self, buffer_m=50) -> None:
        """Filters out short / green paths with nearly similar geometries (using "greenest" wins policy when paths overlap).
        """
        cost_attr = 'aqc_norm' if (self.routing_mode == RoutingMode.CLEAN) else 'nei_norm'
        unique_paths_names = path_overlay_filter.get_unique_paths_by_geom_overlay(
            self.log, 
            self.get_all_paths(), 
            buffer_m=buffer_m, 
            cost_attr=cost_attr
        )
        if unique_paths_names:
            self.filter_paths_by_names(unique_paths_names)

    def filter_paths_by_names(self, filter_names: List[str]) -> None:
        """Filters out short / green paths by list of path names to keep.
        """
        filtered_green_paths = [path for path in self.green_paths if path.name in filter_names]
        if ('short' not in filter_names):
            self.log.debug('Replacing shortest path with shortest green path')
            shortest_green_path = filtered_green_paths[0]
            shortest_green_path.set_path_type(PathType.SHORT)
            shortest_green_path.set_path_name('short')
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
        return self.__as_geojson_feature_collection(feats)

    def get_edges_as_feature_collection(self) -> dict:        
        for path in [self.shortest_path] + self.green_paths:
            path.aggregate_edge_groups_by_attr(
                aq = self.routing_mode == RoutingMode.CLEAN,
                noise = self.routing_mode == RoutingMode.QUIET
            )
        
        feat_lists = [path.get_edge_groups_as_features() for path in [self.shortest_path] + self.green_paths]

        feats = [feat for feat_list in feat_lists for feat in feat_list]
        return self.__as_geojson_feature_collection(feats)

    def __as_geojson_feature_collection(self, features: List[dict]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": features
        }
