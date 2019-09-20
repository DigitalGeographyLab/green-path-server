import os
import ast
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely import wkt
from shapely.geometry import box
import utils.geometry as geom_utils

bboxes = gpd.read_file('data/extents_grids.gpkg', layer='bboxes')
hel = gpd.read_file('data/extents_grids.gpkg', layer='hel')

def get_noise_polygons():
    noise_data = gpd.read_file('data/data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
    noise_polys = geom_utils.explode_multipolygons_to_polygons(noise_data)
    return noise_polys

def get_city_districts():
    return gpd.read_file('data/extents_grids.gpkg', layer='HSY_kaupunginosat_19')

def get_statfi_grid():
    return gpd.read_file('data/extents_grids.gpkg', layer='r250_hel_tyoalue')

def get_koskela_poly():
    koskela_rows = bboxes.loc[bboxes['name'] == 'koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    # return polygon of Koskela area in epsg:3879
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    # return polygon of Kumpula & Koskela area in epsg:3879
    rows = bboxes.loc[bboxes['name'] == 'koskela_kumpula']
    poly = list(rows['geometry'])[0]
    bounds = geom_utils.project_to_wgs(poly).bounds
    return box(*bounds)

def get_hel_poly(WGS84=False, buffer_m=None):
    # return buffered polygon of Helsinki in either epsg:3879 or WGS84
    poly = list(hel['geometry'])[0]
    if (buffer_m is not None):
        poly = poly.buffer(buffer_m)
    if (WGS84 == True):
        poly = geom_utils.project_to_wgs(poly)
    return poly

def get_network_kumpula():
    graph_undir = load_graphml('kumpula-v2_u_g_f_s.graphml', folder='graphs', directed=False, noises=False)
    return graph_undir

def get_network_kumpula_noise(version=3):
    if (version == 1):
        return load_graphml('kumpula_u_g_n_s.graphml', folder='graphs', directed=False)
    if (version == 2):
        return load_graphml('kumpula-v2_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    if (version == 3):
        return load_graphml('kumpula-v3_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    return None

def get_network_full_noise(version=3):
    if (version == 1):
        return load_graphml('hel_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    if (version == 2):
        return load_graphml('hel-v2_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    if (version == 3):
        return load_graphml('hel-v3_u_g_n2_f_s.graphml', folder='graphs', directed=False)

def load_graphml(filename, folder=None, node_type=int, directed=None, noises=True):
    # read the graph from disk
    path = os.path.join(folder, filename)

    # read as directed or undirected graph
    if (directed == True):
        print('loading directed graph')
        G = nx.MultiDiGraph(nx.read_graphml(path, node_type=node_type))
    else:
        print('loading undirected graph')
        G = nx.MultiGraph(nx.read_graphml(path, node_type=node_type))

    # convert graph crs attribute from saved string to correct dict data type
    G.graph['crs'] = ast.literal_eval(G.graph['crs'])

    if 'streets_per_node' in G.graph:
        G.graph['streets_per_node'] = ast.literal_eval(G.graph['streets_per_node'])

    # convert numeric node tags from string to numeric data types
    for _, data in G.nodes(data=True):
        data['x'] = float(data['x'])
        data['y'] = float(data['y'])

    # convert numeric, bool, and list node tags from string to correct data types
    for _, _, data in G.edges(data=True, keys=False):

        # first parse oneway to bool and length to float - they should always
        # have only 1 value each
        data['length'] = float(data['length'])
        if (noises == True):
            data['noises'] = ast.literal_eval(data['noises'])

        # if geometry attribute exists, load the string as well-known text to
        # shapely LineString
        data['geometry'] = wkt.loads(data['geometry'])

    # remove node_default and edge_default metadata keys if they exist
    if 'node_default' in G.graph:
        del G.graph['node_default']
    if 'edge_default' in G.graph:
        del G.graph['edge_default']
    
    return G
