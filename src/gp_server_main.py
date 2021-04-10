import logging
import traceback
from typing import Tuple, Union, Any
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import gp_server.conf as conf
import gp_server.app.routing as routing
from gp_server.app.aqi_map_data_api import get_aqi_map_data_api
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.graph_aqi_updater import GraphAqiUpdater
from gp_server.app.constants import (TravelMode, RoutingMode, 
    RoutingException, ErrorKey, status_code_by_error)
from gp_server.app.logger import Logger
import common.geometry as geom_utils


app = Flask(__name__)
CORS(app)


# set logging to use gunicorn logger & logging level
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

log = Logger(app_logger=app.logger, b_printing=False)

routing_conf = routing.get_routing_conf()

# initialize graph
G = GraphHandler(log, conf.graph_file)

if conf.clean_paths_enabled:
    aqi_updater = GraphAqiUpdater(log, G, r'aqi_updates/')

# start AQI map data service
aqi_map_data_api = get_aqi_map_data_api(log, r'aqi_updates/')
aqi_map_data_api.start()


@app.route('/')
def hello_world():
    return 'Keep calm and walk green paths.'

@app.route('/aqistatus')
def aqi_status():
    if conf.clean_paths_enabled:
        return jsonify(aqi_updater.get_aqi_update_status_response())
    else:
        return create_error_response(ErrorKey.AQI_ROUTING_NOT_AVAILABLE)

@app.route('/aqi-map-data-status')
def aqi_map_data_status():
    return aqi_map_data_api.get_status()

@app.route('/aqi-map-data')
def aqi_map_data():
    return aqi_map_data_api.get_data()

@app.route('/edge-attrs-near-point/<lat>,<lon>')
def edge_attrs_near_point(lat, lon):
    point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon({'lat': float(lat), 'lon': float(lon)}))
    edge = G.find_nearest_edge(point)
    return jsonify(G.format_edge_dict_for_debugging(edge) if edge else None)


@app.route('/paths/<travel_mode>/<routing_mode>/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def paths(travel_mode, routing_mode, orig_lat, orig_lon, dest_lat, dest_lon):
    try:
        travel_mode = TravelMode(travel_mode)
    except Exception:
        return create_error_response(ErrorKey.INVALID_TRAVEL_MODE_PARAM)

    try:
        routing_mode = RoutingMode(routing_mode)
    except Exception:
        return create_error_response(ErrorKey.INVALID_ROUTING_MODE_PARAM)

    if routing_mode == RoutingMode.CLEAN:
        if (not conf.clean_paths_enabled 
                or not aqi_updater.get_aqi_update_status_response()['aqi_data_updated']):
            return create_error_response(ErrorKey.NO_REAL_TIME_AQI_AVAILABLE)
    
    if travel_mode == TravelMode.WALK and routing_mode == RoutingMode.SAFE:
        return create_error_response(ErrorKey.SAFE_PATHS_ONLY_AVAILABLE_FOR_BIKE)


    od_settings = routing.get_od_settings(
        travel_mode, 
        routing_mode, 
        routing_conf, 
        orig_lat, 
        orig_lon, 
        dest_lat, 
        dest_lon
    )

    od_nodes = None
    try:
        od_nodes = routing.find_or_create_od_nodes(log, G, routing_conf, od_settings)
        path_set = routing.find_least_cost_paths(log, G, routing_conf, od_settings, od_nodes)
        path_FC, edge_FC = routing.process_paths_to_FC(log, G, routing_conf, od_settings, path_set)
        return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC }), 200

    except RoutingException as e:
        log.error(traceback.format_exc())
        return create_error_response(str(e))

    except Exception:
        log.error(traceback.format_exc())
        return create_error_response(ErrorKey.UNKNOWN_ERROR)

    finally:
        if od_nodes: routing.delete_added_graph_features(log, G, od_nodes)
        G.reset_edge_cache()


def create_error_response(error: Union[ErrorKey, str]) -> Tuple[Any, int]:
    error_msg = error.value if isinstance(error, ErrorKey) else error
    code = status_code_by_error.get(error_msg, 500)
    return jsonify({ 'error_key': error_msg }), code


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
