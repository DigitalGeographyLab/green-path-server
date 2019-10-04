import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import geopandas as gpd
from fiona.crs import from_epsg
import utils.files as file_utils
import utils.routing as routing_utils
import utils.geometry as geom_utils
import utils.graphs as graph_utils
import utils.noise_exposures as noise_exps
import utils.quiet_paths as qp_utils
import utils.paths as path_utils
import utils.utils as utils

app = Flask(__name__)
CORS(app)

graph_aqi_update_interval_secs = 20

# INITIALIZE GRAPH
start_time = time.time()
nts = qp_utils.get_noise_tolerances()
db_costs = qp_utils.get_db_costs()
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

utils.print_duration(start_time, 'Graph initialized.')

@app.route('/')
def hello_world():
    return 'Keep calm and walk quiet paths.'

@app.route('/quietpaths/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_short_quiet_paths(from_lat, from_lon, to_lat, to_lon):
    # parse query
    start_time = time.time()
    from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    print('from:', from_latLon)
    print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)

    # find / create origin & destination nodes
    orig_node, dest_node, orig_link_edges, dest_link_edges = routing_utils.get_orig_dest_nodes_and_linking_edges(graph, from_xy, to_xy, edge_gdf, node_gdf, nts, db_costs)
    utils.print_duration(start_time, 'Origin & destination nodes set.')
    
    if (orig_node is None):
        print('could not find origin node at', from_latLon)
        return jsonify({'error': 'Origin not found'})
    if (dest_node is None):
        print('could not find destination node at', to_latLon)
        return jsonify({'error': 'Destination not found'})

    # calculate least cost paths
    start_time = time.time()
    path_list = []
    shortest_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight='length')
    if (shortest_path is None):
        return jsonify({'error': 'Could not find paths'})
    # aggregate (combine) path geometry & noise attributes 
    path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, shortest_path, weight='length', noises=True)
    path_list.append({**path_geom_noises, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # calculate quiet paths
    for nt in nts:
        # set name for the noise cost attribute (edge cost)
        noise_cost_attr = 'nc_'+str(nt)
        quiet_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        # aggregate (combine) path geometry & noise attributes 
        path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, quiet_path, weight=noise_cost_attr, noises=True)
        path_list.append({**path_geom_noises, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    utils.print_duration(start_time, 'Routing done.')

    start_time = time.time()
    graph_utils.remove_new_node_and_link_edges(graph, new_node=orig_node['node'], link_edges=orig_link_edges)
    graph_utils.remove_new_node_and_link_edges(graph, new_node=dest_node['node'], link_edges=dest_link_edges)
    # list -> gdf
    paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = paths_gdf.drop_duplicates(subset=['type', 'total_length']).sort_values(by=['type', 'total_length'], ascending=[False, True])
    paths_gdf = qp_utils.add_noise_columns_to_path_gdf(paths_gdf, db_costs)
    # gdf -> dicts
    path_dicts = qp_utils.get_quiet_path_dicts_from_qp_df(paths_gdf)
    unique_paths = path_utils.remove_duplicate_geom_paths(path_dicts, tolerance=30, cost_attr='nei_norm', logging=False)
    # calculate exposure differences to shortest path
    path_comps = qp_utils.get_short_quiet_paths_comparison_for_dicts(unique_paths)
    print('graph update time:', path_geom_noises['cost_update_time'])
    utils.print_duration(start_time, 'Processed paths.')
    return jsonify(path_comps)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
