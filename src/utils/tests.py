"""
This module provides functions needed in the tests. 

"""

from typing import List, Set, Dict, Tuple, Optional
from flask import jsonify
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
from utils.path_finder import PathFinder

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

def get_short_quiet_paths(graph, edge_gdf, node_gdf, from_latLon, to_latLon, nts, db_costs, logging=False) -> dict:
    """Calculates and aggregates short and quiet paths similarly as in the quiet paths application.

    Returns:
        A FeatureCollection (GeoJSON schema) containing a short & quiet paths.
    """
    debug = False

    FC = None
    path_finder = PathFinder('quiet', from_latLon['lat'], from_latLon['lon'], to_latLon['lat'], to_latLon['lon'], debug=debug)

    try:
        path_finder.find_origin_dest_nodes(graph, edge_gdf, node_gdf)
        path_finder.find_least_cost_paths(graph)
        FC = path_finder.process_paths_to_FC(graph)
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        path_finder.delete_added_graph_features(graph)

    # return jsonify(FC)

    return FC
