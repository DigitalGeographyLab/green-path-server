import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import utils.utils as utils
import utils.graphs as graph_utils
import utils.graph_loader as graph_loader
from utils.path_finder import PathFinder

app = Flask(__name__)
CORS(app)

graph_aqi_update_interval_secs: int = 20
debug: bool = True

# load graph data
start_time = time.time()
graph, edge_gdf, node_gdf, edges_sind, nodes_sind = graph_loader.load_graph_data(subset=True)

# setup scheduled graph updater
def edge_attr_update():
    timenow = datetime.now().strftime("%H:%M:%S")
    edge_gdf['updatetime'] =  timenow
    graph_utils.update_edge_attr_to_graph(graph, edge_gdf, df_attr='updatetime', edge_attr='updatetime')
    # TODO load AQI layer, spatially join AQI values to edge_gdf
    # TODO calculate AQI costs to edge_gdf, update AQI costs to graph
    print('updated graph at:', timenow)

edge_attr_update()
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
    path_finder = PathFinder('quiet', from_lat, from_lon, to_lat, to_lon, debug=debug)

    try:
        path_finder.find_origin_dest_nodes(graph, edge_gdf, node_gdf, debug=debug)
        path_finder.find_least_cost_paths(graph)
        path_FC = path_finder.process_paths_to_FC(graph, edges=False)

    except Exception as e:
        # PathFinder throws only pretty exception strings so they can be sent to UI
        error = jsonify({'error': str(e)})

    finally:
        # keep graph clean by removing created nodes & edges
        path_finder.delete_added_graph_features(graph)

        if (error is not None):
            return error

    return jsonify({ 'path_FC': path_FC })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
