
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import geopandas as gpd
from fiona.crs import from_epsg
import time
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.graphs as graph_utils
import utils.noise_exposures as noise_exps
import utils.quiet_paths as qp
import utils.utils as utils

app = Flask(__name__)
CORS(app)

# INITIALIZE GRAPH
start_time = time.time()
nts = qp.get_noise_tolerances()
db_costs = qp.get_db_costs()
graph = files.get_graph_full_noise()
# graph = files.get_graph_kumpula_noise() # use this for testing as it loads quicker
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
    orig_node, dest_node, orig_link_edges, dest_link_edges = rt.get_orig_dest_nodes_and_linking_edges(graph, from_xy, to_xy, edge_gdf, node_gdf, nts, db_costs)
    utils.print_duration(start_time, 'Origin & destination nodes set.')
    # return error messages if origin/destination not found
    if (orig_node is None):
        print('could not find origin node at', from_latLon)
        return jsonify({'error': 'Origin not found'})
    if (dest_node is None):
        print('could not find destination node at', to_latLon)
        return jsonify({'error': 'Destination not found'})

    # calculate least cost paths
    start_time = time.time()
    path_list = []
    # calculate shortest path
    shortest_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight='length')
    if (shortest_path is None):
        return jsonify({'error': 'Could not find paths'})
    # aggregate (combine) path geometry & noise attributes 
    path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, shortest_path, weight='length', noises=True)
    path_list.append({**path_geom_noises, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # calculate quiet paths
    for nt in nts:
        # set name for the noise cost attribute (edge cost)
        noise_cost_attr = 'nc_'+str(nt)
        # optimize quiet path by noise_cost_attr as edge cost
        quiet_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        # aggregate (combine) path geometry & noise attributes 
        path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, quiet_path, weight=noise_cost_attr, noises=True)
        path_list.append({**path_geom_noises, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    utils.print_duration(start_time, 'Routing done.')
    start_time = time.time()
    # remove linking edges of the origin / destination nodes
    graph_utils.remove_new_node_and_link_edges(graph, new_node=orig_node['node'], link_edges=orig_link_edges)
    graph_utils.remove_new_node_and_link_edges(graph, new_node=dest_node['node'], link_edges=dest_link_edges)

    # collect quiet paths to gdf -> dict -> json
    paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = paths_gdf.drop_duplicates(subset=['type', 'total_length']).sort_values(by=['type', 'total_length'], ascending=[False, True])
    # add exposures to noise levels higher than specified threshods (dBs)
    paths_gdf['th_noises'] = [noise_exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add percentages of cumulative distances of different noise levels
    paths_gdf['noise_pcts'] = paths_gdf.apply(lambda row: noise_exps.get_noise_pcts(row['noises'], row['total_length']), axis=1)
    # calculate mean noise level
    paths_gdf['mdB'] = paths_gdf.apply(lambda row: noise_exps.get_mean_noise_level(row['noises'], row['total_length']), axis=1)
    # calculate noise exposure index (same as noise cost but without noise tolerance coefficient)
    paths_gdf['nei'] = [round(noise_exps.get_noise_cost(noises=noises, db_costs=db_costs), 1) for noises in paths_gdf['noises']]
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
