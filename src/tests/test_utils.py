"""
This module provides functions needed in the tests. 

"""

from typing import List, Set, Dict, Tuple, Optional
from shapely.geometry import Point 
# from flask import jsonify
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, GeometryCollection
from pyproj import CRS
import utils.routing as routing_utils
import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps
from app.path import Path
from app.path_set import PathSet
from app.path_finder import PathFinder
from app.logger import Logger

def get_lat_lon_from_geom(geom: Point) -> Dict[str, float]:
    return { 'lat': round(geom.y, 6), 'lon': round(geom.x,6) }

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
    ods['orig_latLon'] = [get_lat_lon_from_geom(geom) for geom in ods['orig_point']]
    ods['dest_latLon'] = [get_lat_lon_from_geom(geom) for geom in ods['dest_point']]
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
        # basic attrs
        'id': qp_props['id'], 
        'length': qp_props['length'], 
        'len_diff': qp_props['len_diff'],
        'len_diff_rat': qp_props['len_diff_rat'],
        'cost_coeff': qp_props['cost_coeff'],
        # noise attrs
        'mdB': qp_props['mdB'],
        'nei': qp_props['nei'],
        'nei_norm': qp_props['nei_norm'],
        'mdB_diff': qp_props['mdB_diff'],
        'nei_diff': qp_props['nei_diff'],
        'nei_diff_rat': qp_props['nei_diff_rat'],
        'path_score': qp_props['path_score'],
        'noise_pcts_sum': noise_exps.get_total_noises_len(qp_props['noise_pcts']),
        'noise_diff_sum': noise_exps.get_total_noises_len(qp_props['noises_diff']),
        # geometrical length
        'geom_length': round(geom_utils.project_geom(shape(qp_feat['geometry'])).length,1)
        }

    return qp_prop_dict

def get_cp_feat_props_from_FC(FC):
    cp_feat = None
    for feature in FC:
        if (feature['properties']['type'] == 'clean'):
            cp_feat = feature
            break
    if (cp_feat is None):
        return {}

    cp_props = cp_feat['properties']
    cp_prop_dict = {
        # basic attrs
        'id': cp_props['id'], 
        'length': cp_props['length'], 
        'len_diff': cp_props['len_diff'],
        'len_diff_rat': cp_props['len_diff_rat'],
        'cost_coeff': cp_props['cost_coeff'],
        # aq attrs
        'aqi_m': cp_props['aqi_m'],
        'aqc': cp_props['aqc'],
        'aqc_norm': cp_props['aqc_norm'],
        'aqi_cl_exps': cp_props['aqi_cl_exps'],
        'aqi_pcts': cp_props['aqi_pcts'],
        'aqi_m_diff': cp_props['aqi_m_diff'],
        'aqc_diff': cp_props['aqc_diff'],
        'aqc_diff_rat': cp_props['aqc_diff_rat'],
        'aqc_diff_score': cp_props['aqc_diff_score'],
        # geometrical length
        'geom_length': round(geom_utils.project_geom(shape(cp_feat['geometry'])).length,1)
        }

    return cp_prop_dict

def get_short_green_paths(logger: Logger, paths_type, G, from_latLon, to_latLon, logging=False) -> dict:
    """Calculates and aggregates short and quiet paths similarly as in the quiet paths application.

    Returns:
        A FeatureCollection (GeoJSON schema) containing a short & quiet paths.
    """

    path_finder = PathFinder(logger, paths_type, G, from_latLon['lat'], from_latLon['lon'], to_latLon['lat'], to_latLon['lon'])

    try:
        path_finder.find_origin_dest_nodes()
        path_finder.find_least_cost_paths()
        path_FC, edge_FC = path_finder.process_paths_to_FC()
    except Exception as e:
        return None # jsonify({'error': str(e)})
    finally:
        path_finder.delete_added_graph_features()

    # return jsonify({ 'path_FC': path_FC, 'edge_FC': edge_FC })

    return path_FC['features']
