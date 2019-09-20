import requests
import json
import polyline
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString
import utils.geometry as geom_utils

def build_plan_query(latlon_from, latlon_to, walkSpeed, max_walk_distance, itins_count, datetime):
    '''
    Function for combining query string for route plan using Digitransit Routing API. 
    Returns
    -------
    <string>
        Digitransit Routing API compatible GraphQL query for querying route plan.
    '''
    return f'''
    plan(
        from: {{lat: {latlon_from['lat']}, lon: {latlon_from['lon']}}}
        to: {{lat: {latlon_to['lat']}, lon: {latlon_to['lon']}}}
        numItineraries: {itins_count},
        walkSpeed: {walkSpeed},
        maxWalkDistance: {max_walk_distance},
        date: "{str(datetime.strftime("%Y-%m-%d"))}",
        time: "{str(datetime.strftime("%H:%M:%S"))}",
    )
    '''

def build_full_route_query(latlon_from, latlon_to, walkSpeed, max_walk_distance, itins_count, datetime):
    '''
    Function for combining query string for full route plan using Digitransit Routing API. 
    Returns
    -------
    <string>
        Digitransit Routing API compatible GraphQL query for querying full route plan.
    '''
    return f'''
    {{
    {build_plan_query(latlon_from, latlon_to, walkSpeed, max_walk_distance, itins_count, datetime)}
        {{
            itineraries {{
                duration
                legs {{
                    mode
                    duration
                    distance
                    legGeometry {{
                        length
                        points
                    }}
                    to {{
                        stop {{
                            gtfsId
                            desc
                            lat
                            lon
                            parentStation {{
                                gtfsId
                                name
                                lat
                                lon
                            }}
                            cluster {{
                                gtfsId
                                name
                                lat
                                lon
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    '''

def run_query(query):
    '''
    Function for running Digitransit Routing API query in the API. 
    Returns
    -------
    <dictionary>
        Results of the query as a dictionary.
    '''
    DT_API_endpoint = 'https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql' 
    headers = {'Content-Type': 'application/json'}
    request = requests.post(DT_API_endpoint, json={'query': query}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception('Query failed to run by returning code of {}. {}'.format(request.status_code, query))

def get_route_itineraries(latlon_from, latlon_to, walkSpeed, datetime, itins_count=3, max_walk_distance=6000):
    '''
    Function for building and running routing query in Digitransit API.
    Returns
    -------
    <list of dictionaries>
        Results of the routing request as list of itineraries
    '''
    query = build_full_route_query(latlon_from, latlon_to, walkSpeed, max_walk_distance, itins_count, datetime)
    # print(query)
    response = run_query(query)
    itineraries = response['data']['plan']['itineraries']
    return itineraries

def reproject_dict_geoms(dictionary):
    dict_c = dict(dictionary)
    for key in dictionary:
        value = dictionary[key]
        if (isinstance(value, Point) or isinstance(value, LineString)):
            dict_c[key] = geom_utils.project_to_etrs(value)
    return dict_c

def dict_values_as_lists(dictionary):
    dict_c = {}
    for key in dictionary:
        dict_c[key] = [dictionary[key]]
    return dict_c

def parse_itin_attributes(itins, from_id, to_id, utilization=1):
    '''
    Function for parsing route geometries got from Digitransit Routing API. 
    Coordinates are decoded from Google Encoded Polyline Algorithm Format.
    Returns
    -------
    <list of dictionaries>
        List of itineraries as dictionaries
    '''
    # walk_gdfs = []
    stop_dicts = []
    # print('itins:', len(itins), 'weight(yht):', weight, 'itin_weight:', itin_weight)
    for itin in itins:
        walk_leg = itin['legs'][0] #TODO fix when origin is at the PT stop, first leg will not be walk but PT (BUS etc.)
        try:
            pt_leg = itin['legs'][1]
        except IndexError:
            pt_leg = {'mode': 'none'}
        geom = walk_leg['legGeometry']['points']
        # parse coordinates from Google Encoded Polyline Algorithm Format
        decoded = polyline.decode(geom)
        # swap coordinates (y, x) -> (x, y)
        coords = [point[::-1] for point in decoded]
        walk = {}
        walk['utilization'] = utilization
        walk['from_axyind'] = from_id
        walk['to_id'] = to_id
        walk['to_pt_mode'] = pt_leg['mode']
        walk['DT_geom'] = geom_utils.create_line_geom(coords)
        walk['DT_walk_dist'] = round(walk_leg['distance'],2)
        walk['DT_origin_latLon'] = geom_utils.get_lat_lon_from_coords(coords[0])
        # walk['first_Point'] = Point(coords[0])
        # walk['DT_last_Point'] = Point(coords[len(coords)-1])
        to_stop = walk_leg['to']['stop']
        walk['stop_id'] = to_stop['gtfsId'] if to_stop != None else ''
        # walk['stop_desc'] = to_stop['desc'] if to_stop != None else ''
        DT_dest_point = geom_utils.get_point_from_lat_lon(to_stop) if to_stop != None else Point(coords[len(coords)-1])
        walk['DT_dest_Point'] = DT_dest_point
        walk['dest_latLon'] = geom_utils.get_lat_lon_from_geom(DT_dest_point)
        # parent_station = to_stop['parentStation'] if to_stop != None else None
        # walk['stop_p_id'] = parent_station['gtfsId'] if parent_station != None else ''
        # walk['stop_p_name'] = parent_station['name'] if parent_station != None else ''
        # walk['stop_p_Point'] = geom_utils.get_point_from_lat_lon(parent_station) if parent_station != None else ''
        # cluster = to_stop['cluster'] if to_stop != None else None
        # walk['stop_c_id'] = cluster['gtfsId'] if cluster != None else ''
        # walk['stop_c_name'] = cluster['name'] if cluster != None else ''
        # walk['stop_c_Point'] = geom_utils.get_point_from_lat_lon(cluster) if cluster != None else ''
        # convert walk dictionary to GeoDataFrame
        # walk_proj = reproject_dict_geoms(walk)
        # walk_data = dict_values_as_lists(walk_proj)
        # walk_gdf = gpd.GeoDataFrame(data=walk_data, geometry=walk_data['path_geom'], crs=from_epsg(3879))
        # walk_gdfs.append(walk_gdf)
        stop_dicts.append(walk)
    # walk_gdf = pd.concat(walk_gdfs).reset_index(drop=True)
    return stop_dicts

