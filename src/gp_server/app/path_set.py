from typing import List, Dict
import gp_server.conf as conf
import gp_server.utils.paths_overlay_filter as path_overlay_filter
from gp_server.app.constants import RoutingMode, PathType, TravelMode, path_type_by_routing_mode
from gp_server.app.logger import Logger
from gp_server.app.path import Path
from gp_server.app.types import edge_group_attr_by_routing_mode


edge_time_attr_by_travel_mode: Dict[TravelMode, str] = {
    TravelMode.WALK: 'length',
    TravelMode.BIKE: 'bike_time_cost'
}

def as_geojson_feature_collection(features: List[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features
    }


class PathSet:
    """An instance of PathSet holds, manipulates and filters both fastest and least cost paths.
    """

    def __init__(self, logger: Logger, routing_mode: RoutingMode, travel_mode: TravelMode):
        self.log = logger
        self.routing_mode = routing_mode
        self.travel_mode = travel_mode
        self.paths: List[Path] = ()

    def set_unique_paths(self, paths: List[Path]) -> None:
        filtered: List[Path] = []
        prev_edge_ids: List[int] = []
        for path in paths:
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

    def sort_bike_paths_by_length(self):
        if len(self.paths) <= 1:
            return

        if self.travel_mode != TravelMode.BIKE:
            raise ValueError('Sort bike paths is for bike paths only')

        self.paths.sort(key=lambda p: getattr(p, 'length'))
    
    def drop_slower_shorter_bike_paths(self):
        """After sorting bike paths by length, it is reasonable to drop shorter paths that
        are slower, so that the remaining paths are in order by both legnth and time.
        """
        if len(self.paths) <= 1:
            return

        if self.travel_mode != TravelMode.BIKE:
            raise ValueError('Drop slower shorter bike paths is for bike paths only')
        
        drop_path_ids = []
        for idx, path in enumerate(self.paths):
            if idx == 0:
                prev_id, prev_length, prev_bike_time = (path.path_id, path.length, path.bike_time_cost)
                continue
            if prev_length < path.length and prev_bike_time > path.bike_time_cost:
                drop_path_ids.append(prev_id)

            prev_id, prev_length, prev_bike_time = (path.path_id, path.length, path.bike_time_cost)

        if drop_path_ids:
            self.paths = [p for p in self.paths if p.path_id not in drop_path_ids]

    def reclassify_path_types(self):
        """After sorting paths by lengths and possibly using drop_slower_shorter_bike_paths,
        the first path of the set needs to be reclassified as fastest and the rest as exposure optimized. 
        """
        exp_path_type = path_type_by_routing_mode[self.routing_mode]
        for idx, path in enumerate(self.paths):
            if idx == 0:
                path.set_path_type(PathType.FASTEST)
                path.set_path_id(PathType.FASTEST.value)
            elif path.path_type == PathType.FASTEST:
                path.set_path_type(exp_path_type)
                path.set_path_id(f'f2')

    def filter_out_exp_optimized_paths_missing_exp_data(self) -> None:
        path_count = len(self.paths)
        if path_count <= 1:
            return

        if self.routing_mode == RoutingMode.GREEN:
            self.paths = [
                path for path in self.paths 
                if (path.path_type == PathType.FASTEST or not path.missing_gvi)
            ]
        if self.routing_mode == RoutingMode.QUIET:
            self.paths = [
                path for path in self.paths 
                if (path.path_type == PathType.FASTEST or not path.missing_noises)
            ]
        if self.routing_mode == RoutingMode.CLEAN:
            self.paths = [
                path for path in self.paths
                if (path.path_type == PathType.FASTEST or not path.missing_aqi)
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
        if len(self.paths) <= 1:
            return
        cost_attr = 'aqc_norm' if self.routing_mode == RoutingMode.CLEAN else 'nei_norm'
        keep_path_ids = path_overlay_filter.get_unique_paths_by_geom_overlay(
            self.log, 
            self.paths, 
            buffer_m=buffer_m, 
            cost_attr=cost_attr
        )
        if keep_path_ids:
            self.filter_paths_by_ids(keep_path_ids)

    def filter_paths_by_ids(self, path_ids: List[str]) -> None:
        """Filters out fast / green paths by list of path IDs to keep.
        """
        filtered_paths = [
            path for path in self.paths if path.path_id in path_ids
        ]
        if PathType.FASTEST.value not in path_ids:
            filtered_paths[0].set_path_type(PathType.FASTEST)
            filtered_paths[0].set_path_id(PathType.FASTEST.value)
        
        self.paths = filtered_paths

    def set_compare_to_fastest_attrs(self) -> None:
        if len(self.paths) <= 1:
            return
        fastest_path = next((
            p for p in self.paths if p.path_type == PathType.FASTEST
        ))
        for path in self.paths:
            if path.path_type != PathType.FASTEST:
                path.set_compare_to_fastest_attrs(fastest_path)

    def get_paths_as_feature_collection(self) -> dict:
        """Returns paths of the set as GeoJSON FeatureCollection (dict). 
        """
        return as_geojson_feature_collection([
                path.get_as_geojson_feature(self.travel_mode) for path in self.paths
            ]
        )

    def get_edges_as_feature_collection(self) -> dict:
        edge_grouping_attr = edge_group_attr_by_routing_mode[self.routing_mode]
        for path in self.paths:
            path.aggregate_edge_groups_by_attr(edge_grouping_attr)
        
        feat_lists = [path.get_edge_groups_as_features() for path in self.paths]

        return as_geojson_feature_collection([
            feat for feat_list in feat_lists for feat in feat_list
            ]
        )
