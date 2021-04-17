from typing import List
from gp_server.app.graph_aqi_updater import GraphAqiUpdater
import time
import gp_server.conf as conf
import common.geometry as geom_utils
import gp_server.app.noise_exposures as noise_exps
import gp_server.app.aq_exposures as aq_exps
import gp_server.app.greenery_exposures as gvi_exps
import gp_server.app.od_handler as od_handler
from common.igraph import Edge as E
from gp_server.app.path import Path
from gp_server.app.path_set import PathSet
from gp_server.app.logger import Logger
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.constants import (
    ErrorKey, PathType, RoutingException, RoutingMode, 
    TravelMode, cost_prefix_dict, path_type_by_routing_mode)
from gp_server.app.types import OdData, OdSettings, RoutingConf


def get_routing_conf() -> RoutingConf:
    return RoutingConf(
        aq_sens = aq_exps.get_aq_sensitivities(),
        gvi_sens = gvi_exps.get_gvi_sensitivities(),
        noise_sens = noise_exps.get_noise_sensitivities(),
        db_costs = noise_exps.get_db_costs(version=3),
        sensitivities_by_routing_mode = {
            RoutingMode.QUIET: noise_exps.get_noise_sensitivities(),
            RoutingMode.CLEAN: aq_exps.get_aq_sensitivities(),
            RoutingMode.GREEN: gvi_exps.get_gvi_sensitivities(),
            RoutingMode.FAST: [],
            RoutingMode.SAFE: []
        },
        fastest_path_cost_attr_by_travel_mode = {
            TravelMode.WALK: E.length,
            TravelMode.BIKE: E.bike_time_cost
        }
     )


def parse_od_settings(        
    path_travel_mode: str,
    path_routing_mode: str,
    routing_conf: RoutingConf,
    orig_lat,
    orig_lon,
    dest_lat,
    dest_lon,
    aqi_updater: GraphAqiUpdater
) -> OdSettings:

    try:
        travel_mode = TravelMode(path_travel_mode)
    except Exception:
        raise RoutingException(ErrorKey.INVALID_TRAVEL_MODE_PARAM.value)

    try:
        if path_routing_mode == 'short':
            # retain support for legacy path variable 'short'
            routing_mode = RoutingMode.FAST
        else:
            routing_mode = RoutingMode(path_routing_mode)
    except Exception:
        raise RoutingException(ErrorKey.INVALID_ROUTING_MODE_PARAM.value)

    if routing_mode == RoutingMode.CLEAN and (not conf.clean_paths_enabled 
                or not aqi_updater.get_aqi_update_status_response()['aqi_data_updated']):
            raise RoutingException(ErrorKey.NO_REAL_TIME_AQI_AVAILABLE.value)
    
    if travel_mode == TravelMode.WALK and routing_mode == RoutingMode.SAFE:
        raise RoutingException(ErrorKey.SAFE_PATHS_ONLY_AVAILABLE_FOR_BIKE.value)

    orig_latLon = {'lat': float(orig_lat), 'lon': float(orig_lon)}
    dest_latLon = {'lat': float(dest_lat), 'lon': float(dest_lon)}
    orig_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(orig_latLon))
    dest_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(dest_latLon))
    sens = routing_conf.sensitivities_by_routing_mode[routing_mode]
    
    return OdSettings(orig_point, dest_point, travel_mode, routing_mode, sens)


def find_or_create_od_nodes(
    log: Logger,
    G: GraphHandler,
    od_settings: OdSettings
) -> OdData:
    """Finds or creates origin & destination nodes and linking edges.

    Raises:
        RoutingException
    """
    start_time = time.time()
    try:
        od_data = od_handler.get_orig_dest_nodes_and_linking_edges(
            G, od_settings.orig_point, od_settings.dest_point
        )
        log.duration(start_time, 'origin & destination nodes set', unit='ms', log_level='info')

        if od_data.orig_node.id == od_data.dest_node.id:
            raise RoutingException(ErrorKey.OD_SAME_LOCATION.value)

        return od_data

    except RoutingException as e:
        raise e

    except Exception as e:
        raise RoutingException(ErrorKey.ORIGIN_OR_DEST_NOT_FOUND.value)


def __find_fastest_path(G: GraphHandler, od_nodes: OdData, fastest_path_cost_attr: E) -> Path:
    return Path(
        path_id = PathType.FASTEST.value,
        path_type = PathType.FASTEST,
        edge_ids = G.get_least_cost_path(
            od_nodes.orig_node.id,
            od_nodes.dest_node.id,
            weight=fastest_path_cost_attr.value
        )
    )


def __find_safest_path(G: GraphHandler, od_nodes: OdData) -> Path:
    return Path(
        path_id = PathType.SAFEST.value,
        path_type = PathType.SAFEST,
        edge_ids = G.get_least_cost_path(
            od_nodes.orig_node.id,
            od_nodes.dest_node.id,
            weight=E.bike_safety_cost.value
        )
    )


def __find_exp_optimized_paths(G: GraphHandler, od_settings: OdSettings, od_nodes: OdData):
    cost_prefix = cost_prefix_dict[od_settings.travel_mode][od_settings.routing_mode]
    return [
        Path(
            path_id = f'{cost_prefix}{sen}',
            path_type = path_type_by_routing_mode[od_settings.routing_mode],
            edge_ids = G.get_least_cost_path(
                od_nodes.orig_node.id,
                od_nodes.dest_node.id,
                weight=f'{cost_prefix}{sen}'
            ),
            cost_coeff = sen
        )
        for sen in od_settings.sensitivities
    ]


def find_least_cost_paths(
    log: Logger,
    G: GraphHandler,
    routing_conf: RoutingConf,
    od_settings: OdSettings,
    od_nodes: OdData,
) -> PathSet:
    """Finds both fastest and exposure optimized paths. 

    Raises:
        RoutingException
    """
    fastest_path_cost_attr = routing_conf.fastest_path_cost_attr_by_travel_mode[od_settings.travel_mode]
    path_set = PathSet(log, od_settings.routing_mode, od_settings.travel_mode)
    paths: List[Path] = []
    start_time = time.time()
    try:
        if od_settings.routing_mode != RoutingMode.SAFE:
            paths.append(__find_fastest_path(G, od_nodes, fastest_path_cost_attr))

        # add safest path to path set if biking
        if (od_settings.travel_mode == TravelMode.BIKE and
            (not conf.research_mode or od_settings.routing_mode == RoutingMode.SAFE)):
                paths.append(__find_safest_path(G, od_nodes))

        if od_settings.routing_mode not in (RoutingMode.FAST, RoutingMode.SAFE):
            paths.extend(__find_exp_optimized_paths(G, od_settings, od_nodes))
        
        path_set.set_unique_paths(paths)
        log.duration(start_time, 'routing done', unit='ms', log_level='info')

        return path_set
    
    except RoutingException as e:
        raise e

    except Exception as e:
        raise RoutingException(ErrorKey.PATHFINDING_ERROR.value)


def process_paths_to_FC(
    log: Logger, 
    G: GraphHandler, 
    routing_conf: RoutingConf,
    od_settings: OdSettings,
    path_set: PathSet
) -> dict:
    """Loads & collects path attributes from the graph for all paths. Also aggregates and filters out nearly identical 
    paths based on geometries and length. 

    Returns:
        All paths as GeoJSON FeatureCollection (as python dictionary).
    Raises:
        Only meaningful exception strings that can be shown in UI.
    """
    start_time = time.time()
    try:
        path_set.set_path_edges(G)
        path_set.aggregate_path_attrs()

        if conf.research_mode and od_settings.travel_mode == TravelMode.BIKE:
            path_set.sort_bike_paths_by_length()
            path_set.drop_slower_shorter_bike_paths()
            path_set.reclassify_path_types()
        
        path_set.filter_out_exp_optimized_paths_missing_exp_data()
        path_set.set_path_exp_attrs(routing_conf.db_costs)
        path_set.filter_out_unique_geom_paths(buffer_m=50)

        path_set.set_compare_to_fastest_attrs()
        log.duration(start_time, 'aggregated paths', unit='ms', log_level='info')
        
        start_time = time.time()
        path_FC = path_set.get_paths_as_feature_collection()
        edge_FC = path_set.get_edges_as_feature_collection() if not conf.research_mode else None
        log.duration(start_time, 'processed paths & edges to FC', unit='ms', log_level='info')

        if conf.research_mode:
            __reclassify_shortest_path(path_FC)
        
        return (path_FC, edge_FC)
    
    except Exception:
        raise RoutingException(ErrorKey.PATH_PROCESSING_ERROR.value)


def __reclassify_shortest_path(path_FC: dict) -> None:
    path_FC['features'][0]['properties']['type'] = 'short'
    path_FC['features'][0]['properties']['id'] = 'short'


def delete_added_graph_features(G: GraphHandler, od_nodes: OdData):
    """Keeps the graph clean by removing new nodes & edges created during routing from the graph.
    """
    delete_o_node = (od_nodes.orig_node.id,) if od_nodes.orig_link_edges else ()
    delete_d_node = (od_nodes.dest_node.id,) if od_nodes.dest_link_edges else ()
    G.drop_nodes_edges(delete_o_node + delete_d_node)
