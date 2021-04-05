from typing import List, Dict
import gp_server.utils.paths_overlay_filter as path_overlay_filter
from gp_server.app.constants import RoutingMode, PathType, TravelMode, path_type_by_routing_mode
from gp_server.app.logger import Logger
from gp_server.app.path import Path
from gp_server.app.types import edge_group_attr_by_routing_mode


edge_time_attr_by_travel_mode: Dict[TravelMode, str] = {
    TravelMode.WALK: 'length',
    TravelMode.BIKE: 'bike_time_cost'
}


class PathSet:
    """An instance of PathSet holds, manipulates and filters both fastest and least cost paths.
    """

    def __init__(self, logger: Logger, routing_mode: RoutingMode):
        self.log = logger
        self.routing_mode = routing_mode
        self.paths: List[Path] = []

    def add_path(self, path: Path) -> None:
        self.paths.append(path)

    def filter_out_unique_edge_sequence_paths(self) -> None:
        filtered: List[Path] = []
        prev_edge_ids: List[int] = []
        for path in self.paths:
            if path.edge_ids != prev_edge_ids:
                filtered.append(path)
            prev_edge_ids = path.edge_ids
        self.paths = filtered

    def set_path_edges(self, G) -> None:
        for p in self.paths:
            p.set_path_edges(G)

    def aggregate_path_attrs(self) -> None:
        for p in self.paths:
            p.aggregate_path_attrs(self.log)
    
    def filter_out_exp_optimized_paths_missing_exp_data(self) -> None:
        path_count = len(self.paths)
        if path_count == 1:
            return

        if self.routing_mode == RoutingMode.GREEN:
            self.paths = [
                path for path in self.paths 
                if (path.path_type == path_type_by_routing_mode[RoutingMode.FAST] or not path.missing_gvi)
            ]
        if self.routing_mode == RoutingMode.QUIET:
            self.paths = [
                path for path in self.paths 
                if (path.path_type == path_type_by_routing_mode[RoutingMode.FAST] or not path.missing_noises)
            ]
        if self.routing_mode == RoutingMode.CLEAN:
            self.paths = [
                path for path in self.paths
                if (path.path_type == path_type_by_routing_mode[RoutingMode.FAST] or not path.missing_aqi)
            ]
        filtered_out_count = path_count - len(self.paths)
        if filtered_out_count:
            self.log.info(f'Filtered out {filtered_out_count} green paths without exposure data')

    def set_path_exp_attrs(self, db_costs) -> None:
        for path in self.paths:
            path.set_noise_attrs(db_costs)
            path.set_aqi_attrs()
            path.set_gvi_attrs()

    def filter_out_unique_geom_paths(self, buffer_m=50) -> None:
        """Filters out fast / green paths with nearly similar geometries (using "greenest" wins policy when paths overlap).
        """
        cost_attr = 'aqc_norm' if self.routing_mode == RoutingMode.CLEAN else 'nei_norm'
        unique_paths_names = path_overlay_filter.get_unique_paths_by_geom_overlay(
            self.log, 
            self.paths, 
            buffer_m=buffer_m, 
            cost_attr=cost_attr
        )
        if unique_paths_names:
            self.filter_paths_by_names(unique_paths_names)

    def filter_paths_by_names(self, filter_names: List[str]) -> None:
        """Filters out fast / green paths by list of path names to keep.
        """
        filtered_paths = [
            path for path in self.paths if path.name in filter_names
        ]
        if PathType.FASTEST.value not in filter_names:
            filtered_paths[0].set_path_type(PathType.FASTEST)
            filtered_paths[0].set_path_name(PathType.FASTEST.value)
        
        self.paths = filtered_paths

    def ensure_right_path_order(self, travel_mode: TravelMode):
        if len(self.paths) == 1:
            return
        edge_speed_attr = edge_time_attr_by_travel_mode[travel_mode]
        self.paths.sort(key=lambda p: getattr(p, edge_speed_attr))
        exp_path_type = path_type_by_routing_mode[self.routing_mode]
        for idx, path in enumerate(self.paths):
            if idx == 0:
                path.set_path_type(PathType.FASTEST)
                path.set_path_name(PathType.FASTEST.value)
            elif path.path_type == PathType.FASTEST:
                path.set_path_type(exp_path_type)
                path.set_path_name(f'f2')

    def set_compare_to_fastest_attrs(self) -> None:
        if len(self.paths) == 1:
            return
        fastest_path = [
            p for p in self.paths if p.path_type == PathType.FASTEST
        ][0]
        for path in self.paths:
            if path.path_type != PathType.FASTEST:
                path.set_compare_to_fastest_attrs(fastest_path)

    def get_paths_as_feature_collection(self) -> List[dict]:
        feats = [path.get_as_geojson_feature() for path in self.paths]
        return self.__as_geojson_feature_collection(feats)

    def get_edges_as_feature_collection(self) -> dict:
        edge_grouping_attr = edge_group_attr_by_routing_mode[self.routing_mode]
        for path in self.paths:
            path.aggregate_edge_groups_by_attr(edge_grouping_attr)
        
        feat_lists = [path.get_edge_groups_as_features() for path in self.paths]

        feats = [feat for feat_list in feat_lists for feat in feat_list]
        return self.__as_geojson_feature_collection(feats)

    def __as_geojson_feature_collection(self, features: List[dict]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": features
        }
