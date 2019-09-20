import pandas as pd
import geopandas as gpd
import time
import math
import ast
from shapely.geometry import Point
from os import listdir
from os.path import isfile, join
from fiona.crs import from_epsg
import numpy as np
import utils.utils as utils
import utils.DT_API as DT_routing
import utils.DT_utils as DT_utils
import utils.geometry as geom_utils
import utils.times as times
import utils.routing as rt
import utils.networks as nw
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial']
import matplotlib.pyplot as plt

def get_xyind_filenames(path='outputs/YKR_commutes_output/home_stops'):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    files_filtered = [f for f in files if 'DS_Store' not in f]
    return files_filtered

def get_xyind_from_filename(filename):
    name = filename.replace('axyind_', '')
    name = name.replace('.csv', '')
    xyind = int(name)
    return xyind

def parse_xyinds_from_filenames(filenames):
    xyinds = []
    for filename in filenames:
        xyind = get_xyind_from_filename(filename)
        xyinds.append(xyind)
    return xyinds

def get_processed_home_walks(path='outputs/YKR_commutes_output/home_stops'):
    filenames = get_xyind_filenames(path=path)
    return parse_xyinds_from_filenames(filenames)

def get_workplaces_distr_join(workplaces, districts):
    # districts['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in districts['geom_distr_point']]
    workplaces = workplaces.reset_index(drop=True)
    
    # print('count workplaces:', len(workplaces.index))
    # join district id to workplaces based on point polygon intersection
    workplaces_distr_join = gpd.sjoin(workplaces, districts, how='left', op='intersects')
    # drop workplaces that are outside the districts
    workplaces_distr_join = workplaces_distr_join.dropna(subset=['id_distr'])
    # print('count workplaces:', len(workplaces_distr_join.index))
    # print(workplaces_distr_join.head())
    workplaces_distr_join = workplaces_distr_join[['txyind', 'yht', 'geom_work', 'grid_geom', 'id_distr']]

    return workplaces_distr_join

def get_axyinds_to_reprocess(grid, reprocessed):
    stops_files = 'outputs/YKR_commutes_output/home_stops'
    axyfiles = get_xyind_filenames(path=stops_files)
    axyinds_to_reprocess = []
    for axyfile in axyfiles:
        # if idx > 5:
        #     continue
        axyind = get_xyind_from_filename(axyfile)
        grid_centr = list(grid.loc[grid['xyind'] == axyind]['grid_centr'])[0]
        home_stops = pd.read_csv(stops_files+'/'+axyfile)
        latLons = home_stops['DT_origin_latLon'].unique()
        for key in latLons:
            latLon = ast.literal_eval(key)
            latLon_point = geom_utils.get_point_from_lat_lon(latLon)
            point = geom_utils.project_to_etrs(latLon_point, epsg=3067)
            origin_grid_dist = point.distance(grid_centr)
            # print('origin_grid_centr_dist', origin_grid_dist)
            if (origin_grid_dist > 50):
                if (axyind not in axyinds_to_reprocess):
                    axyinds_to_reprocess.append(axyind)
                if (origin_grid_dist > 100):
                    print(axyind, 'origin_grid_dist', origin_grid_dist, 'm')

    print('found to reprocess:', len(axyinds_to_reprocess))
    print('of which reprocessed before:', len(reprocessed))
    to_reprocess = [axyind for axyind in axyinds_to_reprocess if axyind not in reprocessed]
    print('to reprocess (filtered):', len(to_reprocess))
    return to_reprocess

def get_valid_distr_geom(districts, workplaces_distr_join):
    workplace_distr_g = workplaces_distr_join.groupby('id_distr')

    district_dicts = []

    for idx, distr in districts.iterrows():
        # if (distr['id_distr'] != '091_OULUNKYLÄ'):
        #     continue
        d = { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }
        try:
            distr_works = workplace_distr_g.get_group(distr['id_distr'])
            distr_works = gpd.GeoDataFrame(distr_works, geometry='geom_work', crs=from_epsg(3067))
            works_convex_poly = distr_works['geom_work'].unary_union.convex_hull
            # print(works_convex_poly)
            works_convex_poly_buffer = works_convex_poly.buffer(20)
            works_center_point = works_convex_poly_buffer.centroid
            # print(works_center_point)
            distr_works['work_center_dist'] = [round(geom.distance(works_center_point)) for geom in distr_works['geom_work']]
            distr_works = distr_works.sort_values(by='work_center_dist')
            # print(distr_works.head(70))
            center_work = distr_works.iloc[0]
            d['work_center'] = center_work['geom_work']
            d['has_works'] = 'yes'
        except Exception:
            d['work_center'] = distr['geom_distr_poly'].centroid
            d['has_works'] = 'no'
        district_dicts.append(d)

    districts_gdf = gpd.GeoDataFrame(district_dicts, geometry='geom_distr_poly', crs=from_epsg(3067))
    districts_gdf['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in districts_gdf['work_center']]
    return districts_gdf

def get_home_district(geom_home, districts):
    for idx, distr in districts.iterrows():
        if (geom_home.within(distr['geom_distr_poly'])):
            # print('District of the origin', distr['id_distr'])
            return { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }

def test_distr_centers_with_DT(districts_gdf):
    datetime = times.get_next_weekday_datetime(8, 30, skipdays=7)
    test_latLon = {'lat': 60.23122, 'lon': 24.83998}

    distr_valids = {}
    districts_gdf = districts_gdf.copy()
    for idx, distr in districts_gdf.iterrows():
        utils.print_progress(idx, len(districts_gdf), percentages=False)
        try:
            itins = DT_routing.get_route_itineraries(test_latLon, distr['distr_latLon'], '1.6666', datetime, itins_count=3, max_walk_distance=6000)
        except Exception:
            itins = []
        valid = 'yes' if (len(itins) > 0) else 'no'
        distr_valids[distr['id_distr']] = valid

    districts_gdf['DT_valid'] = [distr_valids[id_distr] for id_distr in districts_gdf['id_distr']]
    return districts_gdf

def get_work_destinations_gdf(geom_home, districts, axyind=None, work_rows=None, logging=True):
    home_distr = get_home_district(geom_home, districts)
    # turn work_rows (workplaces) into GDF
    works = gpd.GeoDataFrame(work_rows, geometry='geom_work', crs=from_epsg(3067))
    # convert txyind to string to be used as id
    works['txyind'] = [str(txyind) for txyind in works['txyind']]
    # add distance from home to works table
    works['home_dist'] = [round(geom_home.distance(geometry)) for geometry in works['geom_work']]
    # divide works to remote and close works based on home district and 4 km threshold 
    works['within_home_distr'] = [geom.within(home_distr['geom_distr_poly']) for geom in works['geom_work']]
    close_works = works.query('within_home_distr == True or home_dist < 3000')
    remote_works = works.query('within_home_distr == False and home_dist >= 3000')
    if (close_works.empty == False):
        # rename work_latLon to "to_latLon"
        close_works = close_works.rename(index=str, columns={'work_latLon': 'to_latLon', 'txyind': 'id_destination'})
        # filter out unused columns
        close_works = close_works[['yht', 'to_latLon', 'id_destination']]
        close_works['destination_type'] = 'gridcell'
        close_dests_count = len(close_works.index)
    else: 
        print('no close works found')
        close_dests_count = 0
    if (remote_works.empty == False):
        # join remote workplaces to distrcits by spatial intersection
        distr_works_join = gpd.sjoin(districts, remote_works, how='left', op='intersects')
        # count works per district
        distr_works_grps = pd.pivot_table(distr_works_join, index='id_distr', values='yht', aggfunc=np.sum)
        # filter out districts without works
        distr_works_grps = distr_works_grps.loc[distr_works_grps['yht'] > 0]
        # join district geometry back to works per districts table
        distr_works = pd.merge(distr_works_grps, districts, how='left', on='id_distr')
        distr_works['yht'] = [int(round(yht)) for yht in distr_works['yht']]
        # rename work_latLon and distr_latLon to "to_latLon"
        distr_works = distr_works.rename(index=str, columns={'distr_latLon': 'to_latLon', 'id_distr': 'id_destination'})
        # filter out unused columns
        distr_works = distr_works[['yht', 'to_latLon', 'id_destination']]
        distr_works['destination_type'] = 'district'
        distr_dests_count = len(distr_works.index)
    else: 
        print('no remote works found')
        distr_dests_count = 0

    # set only close works as destinations
    if (close_works.empty == False and remote_works.empty == True):
        destinations = close_works.reset_index(drop=True)
    # set only remote works as destinations
    if (close_works.empty == True and remote_works.empty == False):
        destinations = distr_works.reset_index(drop=True)
    # combine destination dataframes if at both exist
    if (close_works.empty == False and remote_works.empty == False):
        destinations = pd.concat([close_works, distr_works], ignore_index=True, sort=True)
    # no destinations found
    if (close_works.empty == True and remote_works.empty == True):
        total_dests_count = 0
        all_included_works_count = 0
    else:
        total_dests_count = len(destinations.index)
        all_included_works_count = destinations['yht'].sum()

    if (logging == True):
        print('found total:', total_dests_count, 'destinations')
        print('of which:', close_dests_count, 'close destinations')
        print('of which:', distr_dests_count, 'remote destinations')
    if (total_dests_count == 0):
        return None
    # print stats about works inside and outside the districts
    total_works_count = works['yht'].sum()
    distr_works_join = gpd.sjoin(districts, works, how='left', op='intersects')
    all_included_works_count_reference = distr_works_join['yht'].sum()
    work_count_match = 'yes' if all_included_works_count == all_included_works_count_reference  else 'no'
    missing_works = total_works_count - all_included_works_count
    outside_ratio = round(((missing_works)/total_works_count)*100)
    if (logging == True):
        print('work count match:', work_count_match)
        print('sum of all works:', total_works_count)
        print('of which outside analysis:', missing_works, '-', outside_ratio, '%')
    home_work_stats = pd.DataFrame([{ 'axyind': axyind, 'total_dests_count': total_dests_count, 'close_dests_count': close_dests_count, 'distr_dests_count': distr_dests_count, 'total_works_count': total_works_count, 'dest_works_count': all_included_works_count, 'missing_works_count': missing_works, 'outside_ratio': outside_ratio, 'work_count_match': work_count_match }])
    home_work_stats[['axyind', 'total_dests_count', 'close_dests_count', 'distr_dests_count', 'total_works_count', 'dest_works_count', 'missing_works_count', 'outside_ratio', 'work_count_match']]
    return { 'destinations': destinations, 'home_work_stats': home_work_stats, 'total_dests_count': total_dests_count }

def get_adjusted_routing_location(latLon, graph=None, edge_gdf=None, node_gdf=None):
    wgs_point = geom_utils.get_point_from_lat_lon(latLon)
    etrs_point = geom_utils.project_to_etrs(wgs_point)
    point_buffer = etrs_point.buffer(90)
    buffer_random_coords = point_buffer.exterior.coords[0]
    new_point = Point(buffer_random_coords)
    point_xy = geom_utils.get_xy_from_geom(new_point)
    try:
        node = rt.get_nearest_node(graph, point_xy, edge_gdf, node_gdf, logging=False)
        node_geom = nw.get_node_geom(graph, node['node'])
        node_distance = round(node_geom.distance(etrs_point))
        node_geom_wgs = geom_utils.project_to_wgs(node_geom)
        node_latLon = geom_utils.get_lat_lon_from_geom(node_geom_wgs)
        if (node_distance < 130):
            return node_latLon
    except Exception:
        print('no adjusted origin/destination found')
        return latLon
    print('no adjusted origin/destination found')
    return latLon

def get_valid_latLon_for_DT(latLon, distance=60, datetime=None, graph=None, edge_gdf=None, node_gdf=None):
    # try if initial latLon works
    try:
        itins = DT_routing.get_route_itineraries(latLon, {'lat': 60.278320, 'lon': 24.853545}, '1.16666', datetime, itins_count=3, max_walk_distance=2500)
        if (len(itins) > 0):
            print('initial latLon works wiht DT')
            return latLon
    except Exception:
        print('proceed to finding altenative latLon for DT')
    # if original latLon did not work, proceed to finding alternative latLon
    wgs_point = geom_utils.get_point_from_lat_lon(latLon)
    etrs_point = geom_utils.project_to_etrs(wgs_point)
    # create a circle for finding alternative points within a distanece from the original point
    point_buffer = etrs_point.buffer(distance)
    circle_coords = point_buffer.exterior.coords
    # find four points at the buffer distance to try as alternative points in routing
    for n in [0, 1, 2, 3]:
        circle_quarter = len(circle_coords)/4
        circle_place = math.floor(n * circle_quarter)
        circle_point_coords = circle_coords[circle_place]
        circle_point = Point(circle_point_coords)
        point_xy = geom_utils.get_xy_from_geom(circle_point)
        try:
            # find nearest node in the network
            node = rt.get_nearest_node(graph, point_xy, edge_gdf, node_gdf, logging=False)
            node_geom = nw.get_node_geom(graph, node['node'])
            node_distance = round(node_geom.distance(etrs_point))
            node_geom_wgs = geom_utils.project_to_wgs(node_geom)
            node_latLon = geom_utils.get_lat_lon_from_geom(node_geom_wgs)
            # try DT routing to node location
            if (node_distance < 90):
                time.sleep(0.2)
                try:
                    itins = DT_routing.get_route_itineraries(node_latLon, {'lat': 60.278320, 'lon': 24.853545}, '1.16666', datetime, itins_count=3, max_walk_distance=2500)
                    if (len(itins) > 0):
                        print('found DT valid latLon at distance:', node_distance,'-', node_latLon)
                        return node_latLon
                    else:
                        continue
                except Exception:
                    continue
        except Exception:
            print('no node/edge found')
            continue
    print('no DT valid latLon found')
    return None

def get_home_work_walks(axyind=None, work_rows=None, districts=None, datetime=None, walk_speed=None, subset=True, logging=True, graph=None, edge_gdf=None, node_gdf=None):
    stats_path='outputs/YKR_commutes_output/home_workplaces_stats/'
    geom_home = work_rows['geom_home'].iloc[0]
    home_latLon = work_rows['home_latLon'].iloc[0]
    # adjust origin if necessary to work with DT routing requests
    valid_home_latLon = get_valid_latLon_for_DT(home_latLon, distance=45, datetime=datetime, graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)
    if (valid_home_latLon == None):
        return None
    destinations = get_work_destinations_gdf(geom_home, districts, axyind=axyind, work_rows=work_rows, logging=logging)
    if (destinations == None):
        return None
    work_destinations = destinations['destinations']
    home_work_stats = destinations['home_work_stats']
    # filter rows of work_destinations for testing
    work_destinations = work_destinations[:14] if subset == True else work_destinations
    # print('work_destinations', work_destinations)
    # filter out destination if it's the same as origin
    work_destinations = work_destinations[work_destinations.apply(lambda x: str(x['id_destination']) != str(axyind), axis=1)]
    total_origin_workers_flow = work_destinations['yht'].sum()
    if (logging == True):
        print('Routing to', len(work_destinations.index), 'destinations:')
    # get routes to all workplaces of the route
    home_walks_all = []
    for idx, destination in work_destinations.iterrows():
        utils.print_progress(idx, destinations['total_dests_count'], percentages=False)
        # execute routing request to Digitransit API
        try:
            itins = DT_routing.get_route_itineraries(valid_home_latLon, destination['to_latLon'], walk_speed, datetime, itins_count=3, max_walk_distance=2500)
        except Exception:
            print('Error in DT routing request between:', axyind, 'and', destination['id_destination'])
            itins = []
        # if no itineraries got, try adjusting the origin & destination by snapping them to network
        if (len(itins) == 0):
            print('no itineraries got -> try adjusting destination')
            adj_destination = get_valid_latLon_for_DT(destination['to_latLon'], datetime=datetime, graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)
            time.sleep(0.3)
            try:
                itins = DT_routing.get_route_itineraries(valid_home_latLon, adj_destination, walk_speed, datetime, itins_count=3, max_walk_distance=2500)
                print('found', len(itins), 'with adjusted origin & destination locations')
            except Exception:
                print('error in DT routing with adjusted origin & destination')
                itins = []

        od_itins_count = len(itins)
        od_workers_flow = destination['yht']
        if (od_itins_count > 0):
            # calculate utilization of the itineraries for identifying the probability of using the itinerary from the origin
            # based on number of commuters and number of alternative itineraries to the destination
            # if only one itinerary is got for origin-destination (commute flow), utilization equals the number of commutes between the OD pair
            utilization = round(od_workers_flow/od_itins_count, 6)
            od_walk_dicts = DT_routing.parse_itin_attributes(itins, axyind, destination['id_destination'], utilization=utilization)
            home_walks_all += od_walk_dicts
        else:
            print('No DT itineraries got between:', axyind, 'and', destination['id_destination'])
            error_df = pd.DataFrame([{ 'axyind': axyind, 'destination_type': destination['destination_type'], 'destination_id': destination['id_destination'], 'destination_yht': destination['yht'] }])
            error_df.to_csv('outputs/YKR_commutes_output/home_stops_errors/axyind_'+str(axyind)+'_to_'+str(destination['id_destination'])+'.csv')

    # print(home_walks_all)
    # collect walks to stops/destinations to GDF
    if (len(home_walks_all) == 0):
        return None
    home_walks_all_df = pd.DataFrame(home_walks_all)
    home_walks_all_df['uniq_id'] = home_walks_all_df.apply(lambda row: DT_utils.get_walk_uniq_id(row), axis=1)
    # group similar walks and calculate realtive utilization rates of them
    home_walks_g = DT_utils.group_home_walks(home_walks_all_df)
    # check that no commute data was lost in the analysis (flows match)
    total_utilization_sum = round(home_walks_g['utilization'].sum())
    total_probs = round(home_walks_g['prob'].sum())
    works_misings_routing = total_origin_workers_flow - total_utilization_sum
    if (works_misings_routing != 0 or total_probs != 100):
        print('Error: utilization sum of walks does not match the total flow of commuters')
        error_df = pd.DataFrame([{ 'axyind': axyind, 'total_origin_workers_flow': total_origin_workers_flow, 'total_utilization_sum': total_utilization_sum, 'total_probs': total_probs }])
        error_df.to_csv('outputs/YKR_commutes_output/home_stops_errors/axyind_'+str(axyind)+'_no_flow_match.csv')
    home_work_stats['works_misings_routing'] = works_misings_routing
    home_work_stats['works_misings_routing_rat'] = round((works_misings_routing/total_origin_workers_flow)*100, 1)
    home_work_stats['total_probs'] = total_probs
    home_work_stats.to_csv(stats_path+'axyind_'+str(axyind)+'.csv')
    return home_walks_g

def validate_home_stops(home_walks_g):
    df = home_walks_g.dropna(subset=['DT_origin_latLon'])
    df = df.reset_index(drop=True)
    stops_count = len(df.index)
    if (stops_count < 1):
        return '\nNo stops found!!'

def plot_walk_stats(walks_comms_join):

    plt.style.use('default')
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Arial']

    fig, ax = plt.subplots(figsize=(8,5))

    ax.scatter(walks_comms_join['commutes_sum'], walks_comms_join['comms_inclusion'], c='black', s=6)

    ax.set_ylabel('Commutes routed (%)')
    ax.set_xlabel('Commutes per origin')

    ax.xaxis.label.set_size(18)
    ax.yaxis.label.set_size(18)
    ax.tick_params(axis='both', which='major', labelsize=15)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10

    fig.tight_layout()
    return fig
