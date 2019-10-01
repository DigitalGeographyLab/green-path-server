"""
This module provides functions for acquiring walkable & unwalkable graphs from Overpass API using OSMnx. 

Todo:
    * Add utils for switching to python-igraph

"""

import osmnx as ox
import networkx as nx
from fiona.crs import from_epsg

def get_walkable_network_graph(extent_poly_wgs=None) -> nx.Graph:
    """Queries and processes a walkable network graph (undirected) from OSM Overpass API.
    """
    # define filter for acquiring walkable street network graph
    cust_filter = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]'
    # query graph
    g = ox.graph_from_polygon(extent_poly_wgs, custom_filter=cust_filter)
    print('loaded graph of', g.number_of_edges(), 'edges')
    # convert graph to undirected graph
    g_u = ox.get_undirected(g)
    print('converted graph to undirected graph of', g_u.number_of_edges(), 'edges')
    # project graph
    g_u_proj = ox.project_graph(g_u, from_epsg(3879))
    return g_u_proj

def get_unwalkable_network_graph(extent_poly_wgs=None) -> nx.Graph:
    """Queries and processes an unwalkable network graph (undirected) from OSM Overpass API.
    """
    # define filter for acquiring (unwalkable) service roads & service tunnels
    cust_filter_no_tunnels = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]["highway"~"service"]["layer"~"-1|-2|-3|-4|-5|-6|-7"]'
    # query graph
    g = ox.graph_from_polygon(extent_poly_wgs, custom_filter=cust_filter_no_tunnels, retain_all=True)
    print('loaded graph of', g.number_of_edges(), 'edges')
    # convert graph to undirected graph
    g_u = ox.get_undirected(g)
    print('converted graph to undirected graph of', g_u.number_of_edges(), 'edges')
    # project graph
    g_u_proj = ox.project_graph(g_u, from_epsg(3879))
    return g_u_proj
