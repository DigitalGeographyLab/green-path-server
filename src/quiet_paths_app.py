
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import geopandas as gpd
from fiona.crs import from_epsg
import time
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
import utils.quiet_paths as qp
import utils.utils as utils

app = Flask(__name__)
CORS(app)

# INITIALIZE GRAPH
start_time = time.time()
nts = qp.get_noise_tolerances()
db_costs = qp.get_db_costs()
# graph = files.get_network_full_noise()
graph = files.get_network_kumpula_noise()
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
nw.set_graph_noise_costs(graph, edge_gdf, db_costs=db_costs, nts=nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

@app.route('/')
def hello_world():
    return 'Keep calm and walk quiet paths.'

@app.route('/quietpaths/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_short_quiet_paths(from_lat, from_lon, to_lat, to_lon):
    start_time = time.time()
    from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    print('from:', from_latLon)
    print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    # find/create origin and destination nodes
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, nts=nts, db_costs=db_costs)
    dest_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, nts=nts, db_costs=db_costs, orig_node=orig_node)
    if (orig_node is None):
        print('could not find origin node at', from_latLon)
        return jsonify({'error': 'Origin not found'})
    if (dest_node is None):
        print('could not find destination node at', to_latLon)
        return jsonify({'error': 'Destination not found'})
    utils.print_duration(start_time, 'Origin & destination nodes set.')
    # get shortest path
    start_time = time.time()
    path_list = []
    shortest_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight='length')
    if (shortest_path is None):
        return jsonify({'error': 'Could not find paths'})
    path_geom_noises = nw.aggregate_path_geoms_attrs(graph, shortest_path, weight='length', noises=True)
    path_list.append({**path_geom_noises, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        noise_cost_attr = 'nc_'+str(nt)
        shortest_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        path_geom_noises = nw.aggregate_path_geoms_attrs(graph, shortest_path, weight=noise_cost_attr, noises=True)
        path_list.append({**path_geom_noises, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    utils.print_duration(start_time, 'Routing done.')
    start_time = time.time()
    # remove linking edges of the origin / destination nodes
    nw.remove_new_node_and_link_edges(graph, orig_node)
    nw.remove_new_node_and_link_edges(graph, dest_node)
    # collect quiet paths to gdf
    paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = paths_gdf.drop_duplicates(subset=['type', 'total_length']).sort_values(by=['type', 'total_length'], ascending=[False, True])
    # add exposures to noise levels higher than specified threshods (dBs)
    paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add percentages of cumulative distances of different noise levels
    paths_gdf['noise_pcts'] = paths_gdf.apply(lambda row: exps.get_noise_pcts(row['noises'], row['total_length']), axis=1)
    # calculate mean noise level
    paths_gdf['mdB'] = paths_gdf.apply(lambda row: exps.get_mean_noise_level(row['noises'], row['total_length']), axis=1)
    # calculate noise exposure index (same as noise cost but without noise tolerance coefficient)
    paths_gdf['nei'] = [round(exps.get_noise_cost(noises=noises, db_costs=db_costs), 1) for noises in paths_gdf['noises']]
    paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 4), axis=1)
    # gdf to dicts
    path_dicts = qp.get_geojson_from_q_path_gdf(paths_gdf)
    # group paths with nearly identical geometries
    unique_paths = qp.remove_duplicate_geom_paths(path_dicts, tolerance=30, logging=False)
    # calculate exposure differences to shortest path
    path_comps = rt.get_short_quiet_paths_comparison_for_dicts(unique_paths)
    # return paths as GeoJSON (FeatureCollection)
    utils.print_duration(start_time, 'Processed paths.')
    return jsonify(path_comps)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
