"""
This module provides functions needed in the tests. 

"""

from typing import List, Set, Dict, Tuple, Optional
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
import utils.geometry as geom_utils
import utils.routing as routing_utils
import utils.geometry as geom_utils
import utils.graphs as graph_utils
import utils.quiet_paths as qp_utils
import utils.noise_exposures as noise_exps
import utils.utils as utils

def get_update_test_walk_line() -> gpd.GeoDataFrame:
    """Returns a GeoDataFrame containing line geometry to use in tests.
    """
    walk_proj = gpd.read_file('data/tests/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/test/test_walk_line.shp')
    return walk_proj

def get_test_ODs() -> List[dict]:
    """Returns a list of dictionaries containing origin & destination pairs for tests (from a GeoJSON file).
    """
    ods = gpd.read_file('data/tests/test_OD_lines.geojson')
    ods['orig_point'] = [geom.interpolate(0, normalized=True) for geom in ods['geometry']]
    ods['dest_point'] = [geom.interpolate(1, normalized=True) for geom in ods['geometry']]
    ods['orig_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in ods['orig_point']]
    ods['dest_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in ods['dest_point']]
    od_dicts = ods.to_dict(orient='records')
    od_dict = {}
    for od in od_dicts:
        od_dict[int(od['OD'])] = od
    return od_dict

def get_short_quiet_paths(graph, edge_gdf, node_gdf, from_latLon, to_latLon, nts, db_costs, logging=False):
    """Calculates and aggregates short and quiet paths just as in the quiet paths application.

    Returns:
        A GeoDataFrame containing a short & quiet paths.
    """
    # parse query
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)

    # find / create origin & destination nodes
    orig_node, dest_node, orig_link_edges, dest_link_edges = routing_utils.get_orig_dest_nodes_and_linking_edges(graph, from_xy, to_xy, edge_gdf, node_gdf, nts, db_costs)
    # utils.print_duration(start_time, 'Origin & destination nodes set.')
    # return error messages if origin/destination not found
    if (orig_node is None):
        print('could not find origin node at', from_latLon)
        # return jsonify({'error': 'Origin not found'})
    if (dest_node is None):
        print('could not find destination node at', to_latLon)
        # return jsonify({'error': 'Destination not found'})

    # optimize paths
    # start_time = time.time()
    # get shortest path
    path_list = []
    shortest_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight='length')
    path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, shortest_path, weight='length', noises=True)
    path_list.append({**path_geom_noises, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        noise_cost_attr = 'nc_'+str(nt)
        quiet_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        path_geom_noises = graph_utils.aggregate_path_geoms_attrs(graph, quiet_path, weight=noise_cost_attr, noises=True)
        path_list.append({**path_geom_noises, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})

    graph_utils.remove_new_node_and_link_edges(graph, new_node=orig_node['node'], link_edges=orig_link_edges)
    graph_utils.remove_new_node_and_link_edges(graph, new_node=dest_node['node'], link_edges=dest_link_edges)
    # list -> gdf
    paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = paths_gdf.drop_duplicates(subset=['type', 'total_length']).sort_values(by=['type', 'total_length'], ascending=[False, True])
    paths_gdf = qp_utils.add_noise_columns_to_path_gdf(paths_gdf, db_costs)

    return paths_gdf
