from typing import List, Set, Dict, Tuple, Optional
import pandas as pd
import geopandas as gpd
import utils.geometry as geom_utils

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
