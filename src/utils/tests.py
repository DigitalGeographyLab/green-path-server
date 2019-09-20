import pandas as pd
import geopandas as gpd
import utils.geometry as geom_utils

def get_update_test_walk_line():
    walk_proj = gpd.read_file('data/test/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/test/test_walk_line.shp')
    return walk_proj

def get_origin_lat_lon():
    # read locations for routing tests (in WGS)
    locations = gpd.read_file('data/test/test_locations_qp_tests.geojson')
    locations['latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in locations['geometry']]
    origin = locations.query("name == 'Koskela'").copy()
    return list(origin['latLon'])[0]

def get_test_ODs():
    # read OD pairs for routing tests (in WGS)
    ods = gpd.read_file('data/test/test_OD_lines.geojson')
    ods['orig_point'] = [geom.interpolate(0, normalized=True) for geom in ods['geometry']]
    ods['dest_point'] = [geom.interpolate(1, normalized=True) for geom in ods['geometry']]
    ods['orig_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in ods['orig_point']]
    ods['dest_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in ods['dest_point']]
    od_dicts = ods.to_dict(orient='records')
    od_dict = {}
    for od in od_dicts:
        od_dict[int(od['OD'])] = od
    return od_dict
