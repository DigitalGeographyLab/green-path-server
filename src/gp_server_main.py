import logging
import traceback
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import gp_server.env as env
from gp_server.app.aqi_map_data_api import get_aqi_map_data_api
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.graph_aqi_updater import GraphAqiUpdater
from gp_server.app.path_finder import PathFinder
from gp_server.app.constants import TravelMode, RoutingMode, RoutingException, ErrorKeys
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


# initialize graph
G = GraphHandler(log, env.graph_file)

if env.clean_paths_enabled:
    aqi_updater = GraphAqiUpdater(log, G, r'aqi_updates/')

# start AQI map data service
aqi_map_data_api = get_aqi_map_data_api(log, r'aqi_updates/')
aqi_map_data_api.start()


@app.route('/')
def hello_world():
    return 'Keep calm and walk green paths.'

@app.route('/aqistatus')
def aqi_status():
    if env.clean_paths_enabled:
        return jsonify(aqi_updater.get_aqi_update_status_response())
    else:
        return jsonify({'error_key': ErrorKeys.AQI_ROUTING_NOT_AVAILABLE.value})

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


@app.route('/paths/<travel_mode>/<exposure_mode>/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def get_short_quiet_paths(travel_mode, exposure_mode, orig_lat, orig_lon, dest_lat, dest_lon):
    try:
        travel_mode = TravelMode(travel_mode)
    except Exception:
        return jsonify({'error_key': ErrorKeys.INVALID_TRAVEL_MODE_PARAM.value})

    try:
        routing_mode = RoutingMode(exposure_mode)
    except Exception:
        return jsonify({'error_key': ErrorKeys.INVALID_EXPOSURE_MODE_PARAM.value})

    if routing_mode == RoutingMode.CLEAN:
        if (not env.clean_paths_enabled 
                or not aqi_updater.get_aqi_update_status_response()['aqi_data_updated']):
            return jsonify({'error_key': ErrorKeys.NO_REAL_TIME_AQI_AVAILABLE.value})

    path_finder = PathFinder(log, travel_mode, routing_mode, G, orig_lat, orig_lon, dest_lat, dest_lon)

    try:
        path_finder.find_origin_dest_nodes()
        path_finder.find_least_cost_paths()
        path_FC, edge_FC = path_finder.process_paths_to_FC()
        return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC })

    except RoutingException as e:
        log.error(traceback.format_exc())
        return jsonify({'error_key': str(e)})

    except Exception:
        log.error(traceback.format_exc())
        return jsonify({'error_key': ErrorKeys.UNKNOWN_ERROR.value})

    finally:
        path_finder.delete_added_graph_features()
        G.reset_edge_cache()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
