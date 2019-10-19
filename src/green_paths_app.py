import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import utils.utils as utils
from utils.path_finder import PathFinder

app = Flask(__name__)
CORS(app)

graph_aqi_update_interval_secs: int = 20
debug: bool = True

# INITIALIZE GRAPH
start_time = time.time()
nts = noise_exps.get_noise_tolerances()
db_costs = noise_exps.get_db_costs()
# graph = file_utils.load_graph_full_noise()
graph = file_utils.load_graph_kumpula_noise() # use this for testing (it loads quicker)
print('Graph of', graph.size(), 'edges read.')
edge_gdf = graph_utils.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = graph_utils.get_node_gdf(graph)
print('Graph features extracted.')
graph_utils.set_graph_noise_costs(graph, edge_gdf, db_costs=db_costs, nts=nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')

# setup scheduled graph updater
def edge_attr_update():
    timenow = datetime.now().strftime("%H:%M:%S")
    edge_gdf['updatetime'] =  timenow
    graph_utils.update_edge_attr_to_graph(graph, edge_gdf, df_attr='updatetime', edge_attr='updatetime')
    # TODO: 1) load AQI layer 2) spatially join AQI values to edge_gdf
    #       3) calculate AQI costs to edge_gdf 4) update AQI costs to graph
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

    FC = None
    path_finder = PathFinder('quiet', from_lat, from_lon, to_lat, to_lon, debug=debug)

    try:
        path_finder.find_origin_dest_nodes(graph, edge_gdf, node_gdf)
        path_finder.find_least_cost_paths(graph)
        FC = path_finder.process_paths_to_FC(graph)
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        path_finder.delete_added_graph_features(graph)

    return jsonify(FC)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
