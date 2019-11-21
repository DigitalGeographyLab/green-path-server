import logging
import time
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import utils.utils as utils
from utils.path_finder import PathFinder
from utils.graph_handler import GraphHandler
from utils.graph_aqi_updater import GraphAqiUpdater
from utils.logger import Logger

# version: 1.1.0

app = Flask(__name__)
CORS(app)
logger = Logger(app_logger=app.logger)

debug: bool = False

# initialize graph
G = GraphHandler(subset=True, set_noise_costs=True)

# start graph aqi updater
aqi_updater = GraphAqiUpdater(G, start=True)

@app.route('/')
def hello_world():
    return 'Keep calm and walk green paths.'

@app.route('/aqistatus')
def aqi_status():
    response = { 
        'b_updated': aqi_updater.bool_graph_aqi_is_up_to_date(), 
        'latest_data': aqi_updater.aqi_data_latest, 
        'update_time_utc': aqi_updater.get_aqi_update_time_str(), 
        'updated_since_secs': aqi_updater.get_aqi_updated_since_secs()
        }
    return jsonify(response)

@app.route('/quietpaths/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def get_short_quiet_paths(orig_lat, orig_lon, dest_lat, dest_lon):

    error = None
    path_finder = PathFinder('quiet', G, orig_lat, orig_lon, dest_lat, dest_lon, debug=debug)

    try:
        path_finder.find_origin_dest_nodes()
        path_finder.find_least_cost_paths()
        path_FC, edge_FC = path_finder.process_paths_to_FC()

    except Exception as e:
        # PathFinder throws only pretty exception strings so they can be sent to UI
        error = jsonify({'error': str(e)})

    finally:
        # keep graph clean by removing created nodes & edges
        path_finder.delete_added_graph_features()

        if (error is not None):
            return error

    return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC })

if __name__ != '__main__':
    # set logging to use gunicorn logger & logging level
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
