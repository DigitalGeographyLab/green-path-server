import logging
import os
from flask import Flask
from flask_cors import CORS
from flask import jsonify
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater
from app.path_finder import PathFinder
from app.logger import Logger

# version: 1.3

app = Flask(__name__)
CORS(app)

# set logging to use gunicorn logger & logging level
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

logger = Logger(app_logger=app.logger)

# initialize graph
G = GraphHandler(logger, subset=eval(os.getenv('GRAPH_SUBSET', 'False')))
aqi_updater = GraphAqiUpdater(logger, G)

@app.route('/')
def hello_world():
    return 'Keep calm and walk green paths.'

@app.route('/aqistatus')
def aqi_status():
    return jsonify(aqi_updater.get_aqi_update_status_response())

@app.route('/quietpaths/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def get_short_quiet_paths(orig_lat, orig_lon, dest_lat, dest_lon):
    return get_green_paths('quiet', orig_lat, orig_lon, dest_lat, dest_lon)

@app.route('/cleanpaths/<orig_lat>,<orig_lon>/<dest_lat>,<dest_lon>')
def get_short_clean_paths(orig_lat, orig_lon, dest_lat, dest_lon):
    if (aqi_updater.get_aqi_updated_since_secs() is not None):
        return get_green_paths('clean', orig_lat, orig_lon, dest_lat, dest_lon)
    else:
        return jsonify({'error': 'latest air quality data not available'})

def get_green_paths(path_type: str, orig_lat, orig_lon, dest_lat, dest_lon):
    error = None
    path_finder = PathFinder(logger, path_type, G, orig_lat, orig_lon, dest_lat, dest_lon)

    try:
        path_finder.find_origin_dest_nodes()
        path_finder.find_least_cost_paths()
        path_FC, edge_FC = path_finder.process_paths_to_FC()

    except Exception as e:
        error = jsonify({'error': str(e)})

    finally:
        # keep the graph clean by removing nodes & edges created during routing
        path_finder.delete_added_graph_features()
        G.reset_edge_cache()

        if error:
            return error

    return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
