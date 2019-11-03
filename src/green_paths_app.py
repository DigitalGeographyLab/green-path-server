import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import utils.utils as utils
from utils.path_finder import PathFinder
from utils.graph_handler import GraphHandler

# version: 1.1.0

app = Flask(__name__)
CORS(app)

graph_aqi_update_interval_secs: int = 20
debug: bool = False

# initialize graph
start_time = time.time()
G = GraphHandler(subset=False)
G.set_noise_costs_to_edges()

# setup scheduled graph updater
def edge_attr_update():
    # TODO load AQI layer, calculate & update AQI costs to graph
    G.update_current_time_to_graph(debug)

graph_updater = BackgroundScheduler()
graph_updater.add_job(edge_attr_update, 'interval', seconds=graph_aqi_update_interval_secs)
# graph_updater.start()

utils.print_duration(start_time, 'graph initialized')

@app.route('/')
def hello_world():
    return 'Keep calm and walk quiet paths.'

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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
