"""
This module provides functions needed in the tests. 

"""

from typing import List, Set, Dict, Tuple, Optional
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
import utils.routing as routing_utils
import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps
import utils.graphs as graph_utils
import utils.utils as utils
from utils.path import Path
from utils.path_set import PathSet

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

def get_qp_feat_props_from_FC(FC):
    qp_feat = None
    for feature in FC:
        if (feature['properties']['type'] == 'quiet'):
            qp_feat = feature
            break
    if (qp_feat is None):
        return {}

    qp_props = qp_feat['properties']
    qp_prop_dict = {
        'id': qp_props['id'], 
        'length': qp_props['length'], 
        'len_diff': qp_props['len_diff'],
        'len_diff_rat': qp_props['len_diff_rat'],
        'cost_coeff': qp_props['cost_coeff'],
        'mdB': qp_props['mdB'],
        'nei': qp_props['nei'],
        'nei_norm': qp_props['nei_norm'],
        'mdB_diff': qp_props['mdB_diff'],
        'nei_diff': qp_props['nei_diff'],
        'nei_diff_rat': qp_props['nei_diff_rat'],
        'path_score': qp_props['path_score'],
        'noise_pcts_sum': noise_exps.get_total_noises_len(qp_props['noise_pcts']),
        'noise_diff_sum': noise_exps.get_total_noises_len(qp_props['noises_diff'])
        }

    return qp_prop_dict

def get_short_quiet_paths(graph, edge_gdf, node_gdf, from_latLon, to_latLon, nts, db_costs, logging=False):
    """Calculates and aggregates short and quiet paths just as in the quiet paths application.

    Returns:
        A GeoDataFrame containing a short & quiet paths.
    """
    debug = False

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

    # find least cost paths
    # start_time = time.time()
    path_set = PathSet(set_type='quiet', debug_mode=debug)
    shortest_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight='length')
    # if (shortest_path is None):
        # return jsonify({'error': 'Could not find paths'})
    path_set.set_shortest_path(Path(nodes=shortest_path, name='short_p', path_type='short', cost_attr='length'))
    for nt in nts:
        noise_cost_attr = 'nc_'+ str(nt)
        quiet_path = routing_utils.get_least_cost_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        path_set.add_green_path(Path(nodes=quiet_path, name='q_'+str(nt), path_type='quiet', cost_attr=noise_cost_attr, cost_coeff=nt))
    # utils.print_duration(start_time, 'routing done')
    
    # find edges of the paths from the graph
    path_set.set_path_edges(graph)

    # keep the garph clean by removing new nodes & edges created before routing
    graph_utils.remove_new_node_and_link_edges(graph, new_node=orig_node['node'], link_edges=orig_link_edges)
    graph_utils.remove_new_node_and_link_edges(graph, new_node=dest_node['node'], link_edges=dest_link_edges)

    # start_time = time.time()
    path_set.aggregate_path_attrs(noises=True)
    path_set.filter_out_unique_len_paths()
    path_set.set_path_noise_attrs(db_costs)
    path_set.filter_out_unique_geom_paths(buffer_m=50)
    path_set.set_green_path_diff_attrs()
    # utils.print_duration(start_time, 'aggregated paths')

    # start_time = time.time()
    FC = path_set.get_as_feature_collection()

    return FC
