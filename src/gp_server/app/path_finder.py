from typing import List, Dict
import time
import gp_server.conf as conf
import gp_server.app.noise_exposures as noise_exps 
import gp_server.app.aq_exposures as aq_exps 
import gp_server.app.greenery_exposures as gvi_exps 
import common.geometry as geom_utils
import gp_server.app.od_handler as od_handler
from gp_server.app.path import Path
from gp_server.app.path_set import PathSet
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.constants import (TravelMode, RoutingMode, 
    PathType, RoutingException, ErrorKey, cost_prefix_dict, path_type_by_routing_mode)
from gp_server.app.logger import Logger
from common.igraph import Edge as E


sensitivities_by_routing_mode: Dict[RoutingMode, List[float]] = {
    RoutingMode.QUIET: noise_exps.get_noise_sensitivities(),
    RoutingMode.CLEAN: aq_exps.get_aq_sensitivities(),
    RoutingMode.GREEN: gvi_exps.get_gvi_sensitivities()
}

fastest_route_edge_attr_by_travel_mode: Dict[TravelMode, E] = {
    TravelMode.WALK: E.length,
    TravelMode.BIKE: E.bike_time_cost
}

class PathFinder:
    """An instance of PathFinder is responsible for orchestrating all routing related tasks from finding the 
    origin & destination nodes to returning the paths as GeoJSON feature collection.
    
    """

    def __init__(
        self,
        logger: Logger,
        travel_mode: TravelMode,
        routing_mode: RoutingMode,
        G: GraphHandler,
        orig_lat,
        orig_lon,
        dest_lat,
        dest_lon
    ):
        self.log = logger
        self.travel_mode = travel_mode
        self.routing_mode = routing_mode
        self.G = G
        orig_latLon = {'lat': float(orig_lat), 'lon': float(orig_lon)}
        dest_latLon = {'lat': float(dest_lat), 'lon': float(dest_lon)}
        self.orig_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(orig_latLon))
        self.dest_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(dest_latLon))
        self.noise_sens = noise_exps.get_noise_sensitivities()
        self.aq_sens = aq_exps.get_aq_sensitivities()
        self.path_set = PathSet(self.log, routing_mode)
        self.orig_node = None
        self.dest_node = None
        self.orig_link_edges = None
        self.dest_link_edges = None
        self.log.debug(f'Initialized path finder: {orig_latLon} - {dest_latLon} - {routing_mode} - {travel_mode}')

    def find_origin_dest_nodes(self):
        """Finds & sets origin & destination nodes and linking edges as instance variables.

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        start_time = time.time()
        try:
            orig_node, dest_node, orig_link_edges, dest_link_edges = od_handler.get_orig_dest_nodes_and_linking_edges(
                self.log, self.G, self.orig_point, self.dest_point, self.aq_sens, self.noise_sens, self.G.db_costs)
            self.orig_node = orig_node
            self.dest_node = dest_node
            self.orig_link_edges = orig_link_edges
            self.dest_link_edges = dest_link_edges
            self.log.duration(start_time, 'origin & destination nodes set', unit='ms', log_level='info')

        except RoutingException as e:
            raise e

        except Exception as e:
            raise RoutingException(ErrorKey.ORIGIN_OR_DEST_NOT_FOUND.value)

        if (self.orig_node == self.dest_node):
            raise RoutingException(ErrorKey.OD_SAME_LOCATION.value)

    def find_safest_path(self) -> Path:
        safest_path_edges = self.G.get_least_cost_path(
            self.orig_node['node'],
            self.dest_node['node'],
            weight=E.bike_safety_cost.value
        )
        return Path(
            orig_node = self.orig_node['node'],
            edge_ids = safest_path_edges,
            name = PathType.SAFEST.value,
            path_type = PathType.SAFEST
        )

    def find_least_cost_paths(self):
        """Finds both fastest and least cost paths. 

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        fastest_route_edge_weight = fastest_route_edge_attr_by_travel_mode[self.travel_mode]
        
        start_time = time.time()
        try:
            if self.routing_mode != RoutingMode.SAFE:
                fastest_path = self.G.get_least_cost_path(
                    self.orig_node['node'],
                    self.dest_node['node'],
                    weight=fastest_route_edge_weight.value
                )
                self.path_set.add_path(
                    Path(
                        orig_node = self.orig_node['node'],
                        edge_ids = fastest_path,
                        name = PathType.FASTEST.value,
                        path_type = PathType.FASTEST
                    )
                )

            # add safest path to path set if biking
            if (self.travel_mode == TravelMode.BIKE and
                (self.routing_mode == RoutingMode.SAFE or not conf.research_mode)):
                    self.path_set.add_path(self.find_safest_path())

            if self.routing_mode not in (RoutingMode.FAST, RoutingMode.SAFE):
                sens = sensitivities_by_routing_mode[self.routing_mode]
                cost_prefix = cost_prefix_dict[self.travel_mode][self.routing_mode]
                
                for sen in sens:
                    cost_attr = cost_prefix + str(sen)
                    least_cost_path = self.G.get_least_cost_path(
                        self.orig_node['node'], 
                        self.dest_node['node'], 
                        weight=cost_attr
                    )
                    self.path_set.add_path(
                        Path(
                            orig_node = self.orig_node['node'],
                            edge_ids = least_cost_path,
                            name = cost_attr,
                            path_type = path_type_by_routing_mode[self.routing_mode],
                            cost_coeff = sen
                        )
                    )
            self.log.duration(start_time, 'routing done', unit='ms', log_level='info')

        except RoutingException as e:
            raise e

        except Exception as e:
            raise RoutingException(ErrorKey.PATHFINDING_ERROR.value)

    def process_paths_to_FC(self) -> dict:
        """Loads & collects path attributes from the graph for all paths. Also aggregates and filters out nearly identical 
        paths based on geometries and length. 

        Returns:
            All paths as GeoJSON FeatureCollection (as python dictionary).
        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        start_time = time.time()
        try:
            self.path_set.filter_out_unique_edge_sequence_paths()
            self.path_set.set_path_edges(self.G)
            self.path_set.aggregate_path_attrs()
            self.path_set.filter_out_exp_optimized_paths_missing_exp_data()
            self.path_set.set_path_exp_attrs(self.G.db_costs)
            self.path_set.filter_out_unique_geom_paths(buffer_m=50)

            if conf.research_mode:
                self.path_set.ensure_right_path_order(self.travel_mode)

            self.path_set.set_compare_to_fastest_attrs()
            self.log.duration(start_time, 'aggregated paths', unit='ms', log_level='info')
            
            start_time = time.time()
            path_FC = self.path_set.get_paths_as_feature_collection()
            edge_FC = self.path_set.get_edges_as_feature_collection() if not conf.research_mode else None
            self.log.duration(start_time, 'processed paths & edges to FC', unit='ms', log_level='info')
            
            return (path_FC, edge_FC)
        
        except Exception:
            raise RoutingException(ErrorKey.PATH_PROCESSING_ERROR.value)

    def delete_added_graph_features(self):
        """Keeps a graph clean by removing new nodes & edges created during routing from the graph.
        """
        self.log.debug('Deleting created nodes & edges from the graph')
        self.G.delete_added_linking_edges(
            orig_edges=self.orig_link_edges,
            orig_node=self.orig_node, 
            dest_edges=self.dest_link_edges,
            dest_node=self.dest_node
        )
