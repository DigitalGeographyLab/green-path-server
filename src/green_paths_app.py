import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import utils.utils as utils
from utils.path_finder import PathFinder
from utils.graph_handler import GraphHandler

app = Flask(__name__)
CORS(app)

graph_aqi_update_interval_secs: int = 20
debug: bool = True

# initialize graph
start_time = time.time()
G = GraphHandler(subset=True)
G.set_noise_costs_to_edges()

# setup scheduled graph updater
def edge_attr_update():
    # TODO load AQI layer, calculate & update AQI costs to graph
    G.update_current_time_to_graph()

graph_updater = BackgroundScheduler()
graph_updater.add_job(edge_attr_update, 'interval', seconds=graph_aqi_update_interval_secs)
graph_updater.start()

utils.print_duration(start_time, 'graph initialized')

@app.route('/')
def hello_world():
    return 'Keep calm and walk quiet paths.'

@app.route('/quietpaths/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_short_quiet_paths(from_lat, from_lon, to_lat, to_lon):

    error = None
    path_finder = PathFinder('quiet', G, from_lat, from_lon, to_lat, to_lon, debug=debug)

    try:
        path_finder.find_origin_dest_nodes(debug=debug)
        path_finder.find_least_cost_paths()
        path_FC = path_finder.process_paths_to_FC(edges=False)

    except Exception as e:
        # PathFinder throws only pretty exception strings so they can be sent to UI
        error = jsonify({'error': str(e)})

    finally:
        # keep graph clean by removing created nodes & edges
        path_finder.delete_added_graph_features()

        if (error is not None):
            return error

    return jsonify({ 'path_FC': path_FC })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
