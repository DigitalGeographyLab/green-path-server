import logging
import traceback
import os
from flask import Flask
from flask_cors import CORS
from flask import jsonify
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater
from app.path_finder import PathFinder
from app.constants import TravelMode, RoutingMode, RoutingException, ErrorKeys
from app.logger import Logger
import utils.geometry as geom_utils

# version: 1.4

app = Flask(__name__)
CORS(app)

# set logging to use gunicorn logger & logging level
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

log = Logger(app_logger=app.logger)

# initialize graph
G = GraphHandler(log, subset=eval(os.getenv('GRAPH_SUBSET', 'False')))
aqi_updater = GraphAqiUpdater(log, G)

@app.route('/')
def hello_world():
    return 'Keep calm and walk green paths.'

@app.route('/paths/<travel_mode>/<routing_mode>/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def get_short_quiet_paths(travel_mode, routing_mode, orig_lat, orig_lon, dest_lat, dest_lon):
    try:
        travel_mode = TravelMode(travel_mode)
        routing_mode = RoutingMode(routing_mode)
    except Exception as e:
        return jsonify({'error_key': 'routing.invalid_travel_or_routing_mode_in_request'})

    if (routing_mode == RoutingMode.CLEAN and not aqi_updater.get_aqi_updated_since_secs()):
        return jsonify({'error_key': 'routing.no_real_time_aqi_available'})

    error = None
    try:
        path_finder = PathFinder(log, travel_mode, routing_mode, G, orig_lat, orig_lon, dest_lat, dest_lon)
        path_finder.find_origin_dest_nodes()
        path_finder.find_least_cost_paths()
        path_FC, edge_FC = path_finder.process_paths_to_FC()

    except RoutingException as e:
        log.error(traceback.format_exc())
        error = jsonify({'error_key': str(e)})

    except Exception as e:
        log.error(traceback.format_exc())
        error = jsonify({'error_key': ErrorKeys.UNKNOWN_ERROR.value})

    finally:
        path_finder.delete_added_graph_features()
        G.reset_edge_cache()

        if error:
            return error

    return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC })

@app.route('/aqistatus')
def aqi_status():
    return jsonify(aqi_updater.get_aqi_update_status_response())

@app.route('/edge-attrs-near-point/<lat>,<lon>')
def edge_attrs_near_point(lat, lon):
    point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon({'lat': float(lat), 'lon': float(lon)}))
    edge = G.find_nearest_edge(point)
    return jsonify(G.format_edge_dict_for_debugging(edge) if edge else None)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
