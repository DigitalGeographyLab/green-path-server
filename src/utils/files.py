"""
This module provides functions for loading noise & graph data from external files into application.

"""

import os
import ast
import geopandas as gpd
import networkx as nx
from shapely import wkt
from shapely.geometry import box, Polygon
import utils.geometry as geom_utils

def get_noise_polygons() -> gpd.GeoDataFrame:
    """Returns noise polygons (for Helsinki) as GeoDataFrame in EPSG 3879
    """
    noise_data = gpd.read_file('data/noise_data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
    noise_polys = geom_utils.explode_multipolygons_to_polygons(noise_data)
    return noise_polys

def get_koskela_kumpula_box() -> Polygon:
    """Returns polygon of Kumpula & Koskela area in epsg:4326 (projected from epsg:3879)
    """
    bboxes = gpd.read_file('data/aoi_polygons.gpkg', layer='aoi_bboxes')
    rows = bboxes.loc[bboxes['name'] == 'koskela_kumpula']
    poly = list(rows['geometry'])[0]
    bounds = geom_utils.project_geom(poly, from_epsg=3879, to_epsg=4326).bounds
    return box(*bounds)

def get_hel_poly(WGS84=False, buffer_m=None) -> Polygon:
    """returns buffered polygon for Helsinki in either epsg:3879 or WGS84
    """
    hel_poly = gpd.read_file('data/aoi_polygons.gpkg', layer='hel')
    poly = list(hel_poly['geometry'])[0]
    if (buffer_m is not None):
        poly = poly.buffer(buffer_m)
    if (WGS84 == True):
        poly = geom_utils.project_geom(poly, from_epsg=3879, to_epsg=4326)
    return poly

def load_graph_kumpula_noise(version=3) -> nx.Graph:
    if (version == 3):
        return load_graphml('kumpula-v3_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    else:
        print('No graph found for version:', version)
    return None

def load_graph_full_noise(version=3) -> nx.Graph:
    if (version == 3):
        return load_graphml('hel-v3_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    else:
        print('No graph found for version:', version)
    return None

def load_graphml(filename, folder=None, node_type=int, directed=None, noises=True) -> nx.Graph:
    # read the graph from disk
    path = os.path.join(folder, filename)

    # read as directed or undirected graph
    if (directed == True):
        G = nx.MultiDiGraph(nx.read_graphml(path, node_type=node_type))
    else:
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
