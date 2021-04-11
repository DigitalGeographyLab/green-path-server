from gp_server.app.graph_handler import GraphHandler
from gp_server.app.constants import TravelMode, RoutingMode
import gp_server.app.routing as routing
import pytest


def test_removes_linking_edges_after_routing(
    log, 
    graph_handler: GraphHandler, 
    routing_conf
):
    # paths/walk/green/60.21352729760156,24.97086446863051/60.21128945130093,24.968455167858025
    od_settings = routing.parse_od_settings(
        TravelMode.WALK.value,
        RoutingMode.GREEN.value,
        routing_conf,
        orig_lat = '60.21352729760156',
        orig_lon = '24.97086446863051',
        dest_lat = '60.21128945130093',
        dest_lon = '24.968455167858025',
        aqi_updater = None
    )
    ecount = graph_handler.graph.ecount()
    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    assert ecount + 4 == graph_handler.graph.ecount()
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()
    assert ecount == graph_handler.graph.ecount()


def test_finds_routes_between_existing_OD(
    log, 
    graph_handler: GraphHandler,
    routing_conf,
    ensure_path_fc,
    ensure_edge_fc
):

    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.215175', 
        orig_lon = '24.980636', 
        dest_lat = '60.200423', 
        dest_lon = '24.961936',
        aqi_updater = None
    )

    ecount = graph_handler.graph.ecount()
    assert ecount == 16643

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    assert ecount == graph_handler.graph.ecount()
    ensure_path_fc(path_FC)
    ensure_edge_fc(edge_FC)


def test_finds_routes_between_created_OD(
    log, 
    graph_handler: GraphHandler, 
    routing_conf,
    ensure_path_fc,
    ensure_edge_fc
):
    # paths/walk/green/60.21352729760156,24.97086446863051/60.21128945130093,24.968455167858025
    
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.21352729760156', 
        orig_lon = '24.97086446863051', 
        dest_lat = '60.21128945130093', 
        dest_lon = '24.968455167858025',
        aqi_updater = None
    )

    ecount = graph_handler.graph.ecount()
    assert ecount == 16643

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    ensure_path_fc(path_FC)
    ensure_edge_fc(edge_FC)
    assert ecount + 4 == graph_handler.graph.ecount()
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()



def test_finds_routes_between_created_OD_on_same_street(
    log, 
    graph_handler: GraphHandler, 
    routing_conf
):
    # /paths/walk/quiet/60.214233,24.971411/60.213558,24.970785
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.214233',
        orig_lon = '24.971411',
        dest_lat = '60.213558',
        dest_lon = '24.970785',
        aqi_updater = None
    )

    ecount = graph_handler.graph.ecount()
    assert ecount == 16643

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    assert path_FC['type'] == 'FeatureCollection'
    assert edge_FC['type'] == 'FeatureCollection'
    assert ecount + 4 == graph_handler.graph.ecount()
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()



def test_finds_routes_between_existing_O_and_created_D_on_same_street(
    log, 
    graph_handler: GraphHandler, 
    routing_conf
):
    # /paths/walk/green/60.212149138928254,24.969463681172613/60.213886742565194,24.971240777950726
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.212149138928254',
        orig_lon = '24.969463681172613',
        dest_lat = '60.213886742565194',
        dest_lon = '24.971240777950726',
        aqi_updater = None
    )

    ecount = graph_handler.graph.ecount()
    assert ecount == 16643

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    assert path_FC['type'] == 'FeatureCollection'
    assert edge_FC['type'] == 'FeatureCollection'
    assert ecount + 2 == graph_handler.graph.ecount()
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()


def test_creates_also_dest_node_if_origin_was_created(
    log, 
    graph_handler: GraphHandler, 
    routing_conf
):
    # paths/walk/green/60.213859473184016,24.971143562116595/60.21210611561355,24.969360716643195
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.213859473184016',
        orig_lon = '24.971143562116595',
        dest_lat = '60.21210611561355',
        dest_lon = '24.969360716643195',
        aqi_updater = None
    )

    ecount = graph_handler.graph.ecount()
    assert ecount == 16643

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    assert path_FC['type'] == 'FeatureCollection'
    assert edge_FC['type'] == 'FeatureCollection'
    assert ecount + 4 == graph_handler.graph.ecount() # if origin was already created, then also dest is created
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()


def test_path_props_when_routing_with_created_OD(
    log,
    graph_handler: GraphHandler,
    routing_conf
):
    # paths/walk/green/60.21352729760156,24.97086446863051/60.21128945130093,24.968455167858025
    
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.21352729760156', 
        orig_lon = '24.97086446863051', 
        dest_lat = '60.21128945130093', 
        dest_lon = '24.968455167858025',
        aqi_updater = None
    )

    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()

    path_1 = path_FC['features'][0]
    props = path_1['properties']
    assert props['length'] == 291.97
    assert round(sum(props['noises'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_pcts'].values()),1) == 100.0
    # assert round(sum(props['aqi_cl_exps'].values()),1) == round(props['length'],1)
    # assert round(sum(props['aqi_cl_pcts'].values()),1) == 100.0
    assert round(sum(props['noise_range_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['noise_pcts'].values()),1) == 100.0
    assert props['bike_time_cost'] == 291.93
    assert props['bike_safety_cost'] == 291.93


def test_path_props_when_routing_with_created_D(
    log,
    graph_handler: GraphHandler, 
    routing_conf
):
    # origin is existing node, destination is new
    # paths/walk/quiet/60.212103883291405,24.969382893894505/60.21390217111113,24.971206858808813
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.212103883291405',
        orig_lon = '24.969382893894505',
        dest_lat = '60.21390217111113',
        dest_lon = '24.971206858808813',
        aqi_updater = None
    )
    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()

    path_1 = path_FC['features'][0]
    props = path_1['properties']
    assert props['length'] == 218.58
    assert round(sum(props['noises'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_pcts'].values()),1) == 100.0
    # assert round(sum(props['aqi_cl_exps'].values()),1) == round(props['length'],1)
    # assert round(sum(props['aqi_cl_pcts'].values()),1) == 100.0
    assert round(sum(props['noise_range_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['noise_pcts'].values()),1) == 100.0
    assert props['bike_time_cost'] == 218.52
    assert props['bike_safety_cost'] == 218.52


def test_path_props_when_routing_with_created_OD_on_same_street(
    log, 
    graph_handler: GraphHandler, 
    routing_conf
):
    # /paths/walk/quiet/60.214233,24.971411/60.213558,24.970785
    od_settings = routing.parse_od_settings(
        TravelMode.WALK, 
        RoutingMode.GREEN, 
        routing_conf, 
        orig_lat = '60.214233',
        orig_lon = '24.971411',
        dest_lat = '60.213558',
        dest_lon = '24.970785',
        aqi_updater = None
    )
    od_nodes = routing.find_or_create_od_nodes(log, graph_handler, od_settings)
    path_set = routing.find_least_cost_paths(log, graph_handler, routing_conf, od_settings, od_nodes)
    path_FC, edge_FC = routing.process_paths_to_FC(log, graph_handler, routing_conf, od_settings, path_set)
    routing.delete_added_graph_features(graph_handler, od_nodes)
    graph_handler.reset_edge_cache()
    
    path_1 = path_FC['features'][0]
    props = path_1['properties']
    assert props['length'] == 82.8
    assert round(sum(props['noises'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['gvi_cl_pcts'].values()),1) == 100.0
    # assert round(sum(props['aqi_cl_exps'].values()),1) == round(props['length'],1)
    # assert round(sum(props['aqi_cl_pcts'].values()),1) == 100.0
    assert round(sum(props['noise_range_exps'].values()),1) == round(props['length'],1)
    assert round(sum(props['noise_pcts'].values()),1) == 100.0
    assert props['bike_time_cost'] == 82.8
    assert props['bike_safety_cost'] == 82.8
