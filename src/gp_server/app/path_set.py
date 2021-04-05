from typing import List, Set, Dict, Tuple
import gp_server.utils.paths_overlay_filter as path_overlay_filter
from gp_server.app.constants import RoutingMode, PathType
from gp_server.app.logger import Logger
from gp_server.app.path import Path
from gp_server.app.types import edge_group_attr_by_routing_mode


class PathSet:
    """An instance of PathSet holds, manipulates and filters both fastest and least cost paths.
    """

    def __init__(self, logger: Logger, routing_mode: RoutingMode):
        self.log = logger
        self.routing_mode = routing_mode
        self.fastest_path: Path = None
        self.exp_optimized_paths: List[Path] = []

    def set_fastest_path(self, f_path: Path) -> None:
        self.fastest_path = f_path

    def add_exp_optimized_path(self, g_path: Path) -> None:
        self.exp_optimized_paths.append(g_path)

    def get_all_paths(self) -> List[Path]: return [self.fastest_path] + self.exp_optimized_paths

    def set_path_edges(self, G) -> None:
        """Loads edges for all paths in the set from a graph (based on node lists of the paths).
        """
        if self.fastest_path:
            self.fastest_path.set_path_edges(G)
        for gp in self.exp_optimized_paths:
            gp.set_path_edges(G)

    def aggregate_path_attrs(self) -> None:
        """Aggregates edge level path attributes to paths.
        """
        if self.fastest_path:
            self.fastest_path.aggregate_path_attrs(self.log)
        for gp in self.exp_optimized_paths:
            gp.aggregate_path_attrs(self.log)
    
    def filter_out_exp_optimized_paths_missing_exp_data(self) -> None:
        path_count = len(self.exp_optimized_paths)
        if self.routing_mode == RoutingMode.CLEAN:
            self.exp_optimized_paths = [path for path in self.exp_optimized_paths if not path.missing_aqi]
        if self.routing_mode == RoutingMode.QUIET:
            self.exp_optimized_paths = [path for path in self.exp_optimized_paths if not path.missing_noises]
        filtered_out_count = path_count - len(self.exp_optimized_paths)
        if filtered_out_count:
            self.log.info('Filtered out '+ str(filtered_out_count) + ' green paths without exposure data')

    def filter_out_unique_edge_sequence_paths(self) -> None:
        self.log.debug('Green path count: '+ str(len(self.exp_optimized_paths)))
        filtered = []
        prev_edges = self.fastest_path.edge_ids
        for path in self.exp_optimized_paths:
            if (path.edge_ids != prev_edges):
                filtered.append(path)
            prev_edges = path.edge_ids
        self.exp_optimized_paths = filtered
        self.log.debug('Green path count after filter by unique edge sequence: '+ str(len(self.exp_optimized_paths)))

    def filter_out_unique_geom_paths(self, buffer_m=50) -> None:
        """Filters out fast / green paths with nearly similar geometries (using "greenest" wins policy when paths overlap).
        """
        cost_attr = 'aqc_norm' if self.routing_mode == RoutingMode.CLEAN else 'nei_norm'
        unique_paths_names = path_overlay_filter.get_unique_paths_by_geom_overlay(
            self.log, 
            self.get_all_paths(), 
            buffer_m=buffer_m, 
            cost_attr=cost_attr
        )
        if unique_paths_names:
            self.filter_paths_by_names(unique_paths_names)

    def filter_paths_by_names(self, filter_names: List[str]) -> None:
        """Filters out fast / green paths by list of path names to keep.
        """
        filtered_exp_optimized_paths = [
            path for path in self.exp_optimized_paths if path.name in filter_names
        ]
        if PathType.FASTEST.value not in filter_names:
            self.log.debug('Replacing fastest path with fastest green path')
            fastest_exp_optimized_path = filtered_exp_optimized_paths[0]
            fastest_exp_optimized_path.set_path_type(PathType.FASTEST)
            fastest_exp_optimized_path.set_path_name(PathType.FASTEST.value)
            self.set_fastest_path(fastest_exp_optimized_path)
            filtered_exp_optimized_paths = filtered_exp_optimized_paths[1:]
        self.exp_optimized_paths = filtered_exp_optimized_paths

    def set_path_exp_attrs(self, db_costs) -> None:
        self.fastest_path.set_noise_attrs(db_costs)
        self.fastest_path.set_aqi_attrs()
        self.fastest_path.set_gvi_attrs()
        for path in self.exp_optimized_paths:
            path.set_noise_attrs(db_costs)
            path.set_aqi_attrs()
            path.set_gvi_attrs()

    def set_compare_to_fastest_attrs(self) -> None:
        for path in self.exp_optimized_paths:
            path.set_compare_to_fastest_attrs(self.fastest_path)

    def get_paths_as_feature_collection(self) -> List[dict]:
        feats = [path.get_as_geojson_feature() for path in [self.fastest_path] + self.exp_optimized_paths]
        return self.__as_geojson_feature_collection(feats)

    def get_edges_as_feature_collection(self) -> dict:
        edge_grouping_attr = edge_group_attr_by_routing_mode[self.routing_mode]
        for path in [self.fastest_path] + self.exp_optimized_paths:
            path.aggregate_edge_groups_by_attr(edge_grouping_attr)
        
        feat_lists = [path.get_edge_groups_as_features() for path in [self.fastest_path] + self.exp_optimized_paths]

        feats = [feat for feat_list in feat_lists for feat in feat_list]
        return self.__as_geojson_feature_collection(feats)

    def __as_geojson_feature_collection(self, features: List[dict]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": features
        }
