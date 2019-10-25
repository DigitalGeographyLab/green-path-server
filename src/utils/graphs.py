"""
This module provides various functions for manipulating graphs at graph construction phase.
All graph manipulation that is done at routing time is taken care by class GraphHandler.

Todo:
    * Add support for using other edge weights than noise (e.g. AQI)
    * Try python-igraph (or other faster) library
"""

from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime
import time
import pandas as pd
import geopandas as gpd
import networkx as nx
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString
import utils.noise_exposures as noise_exps
import utils.geometry as geom_utils
import utils.utils as utils

def delete_unused_edge_attrs(graph, save_attrs=['uvkey', 'length', 'geometry', 'noises']) -> None:
    """Removes edge attributes other than the ones listed in save_attrs -arg from the graph.
    """
    for node_from in list(graph.nodes):
        nodes_to = graph[node_from]
        for node_to in nodes_to.keys():
            edges = graph[node_from][node_to]
            for edge_k in edges.keys():
                edge = graph[node_from][node_to][edge_k]
                edge_attrs = list(edge.keys())
                for attr in edge_attrs:
                    if (attr not in save_attrs):
                        del edge[attr]

def add_missing_edge_geometries(graph, edge_dicts: List[dict]) -> None:
    """Updates missing straight line edge geometries to edge attributes in a graph."""
    edge_count = len(edge_dicts)
    for idx, edge_d in enumerate(edge_dicts):
        if ('geometry' not in edge_d):
            node_from = edge_d['uvkey'][0]
            node_to = edge_d['uvkey'][1]
            # interpolate missing geometry as straight line between nodes
            edge_geom = get_edge_geom_from_node_pair(graph, node_from, node_to)
            # set geometry attribute of the edge
            nx.set_edge_attributes(graph, { edge_d['uvkey']: {'geometry': edge_geom} })
        # set length attribute
        nx.set_edge_attributes(graph, { edge_d['uvkey']: {'length': round(edge_d['geometry'].length, 3)} })
        utils.print_progress(idx+1, edge_count, percentages=True)
    print('\nEdge geometries & lengths set.')

def get_edge_geom_from_node_pair(graph, node_1: int, node_2: int) -> LineString:
    """Returns a straight line edge geometry between two nodes.
    """
    node_1_geom = geom_utils.get_point_from_xy(graph.nodes[node_1])
    node_2_geom = geom_utils.get_point_from_xy(graph.nodes[node_2])
    edge_line = LineString([node_1_geom, node_2_geom])
    return edge_line

def osmid_to_string(osmid) -> str:
    """Creates an unique osmid-string (for an edge) from osmid property that can be either string or list of strings.
    """
    if isinstance(osmid, list):
        osm_str = ''
        osmid_list = sorted(osmid)
        for osm_id in osmid_list:
            osm_str += str(osm_id)+'_'
    else:
        osm_str = str(osmid)
    return osm_str

def get_all_edge_dicts(graph, attrs: list = None, by_nodes: bool = True) -> List[dict]:
    """Collects and returns all edges of a graph as a list of dictionaries. 

    Args:
        attrs: A list of edge attributes (keys) that the edge dictionaries should have.
        by_nodes: A boolean value indicating whether the edge dictionaries should be extracted as all connections between nodes or just as the
            set of undirected edges in the graph (which is around half of the total number of connections between nodes). 
    Returns:
        A list of dictionaries containing the edge attributes.
    """
    edge_dicts = []
    if (by_nodes == True):
        for node_from in list(graph.nodes):
            nodes_to = graph[node_from]
            for node_to in nodes_to.keys():
                # all edges between node-from and node-to as dict (usually)
                edges = graph[node_from][node_to]
                # usually only one edge is found between each origin-to-destination-node -pair 
                # edge_k is unique identifier for edge between two nodes, integer (etc. 0 or 1) 
                for edge_k in edges.keys():
                    # combine unique identifier for the edge
                    edge_uvkey = (node_from, node_to, edge_k)
                    ed = { 'uvkey': edge_uvkey }
                    # if attribute list is provided, get only the specified edge attributes
                    if (isinstance(attrs, list)):
                        for attr in attrs:
                            ed[attr] = edges[edge_k][attr]
                    else:
                        ed = edges[edge_k]
                        ed['uvkey'] = edge_uvkey
                    edge_dicts.append(ed)
    else:
        for u, v, k, data in graph.edges(keys=True, data=True):
            edge_uvkey = (u, v, k)
            # edge dict contains all edge attributes
            ed = { 'uvkey': edge_uvkey }
            # if attribute list is provided, get only the specified edge attributes
            if (isinstance(attrs, list)):
                for attr in attrs:
                    ed[attr] = data[attr]
            else:
                ed = data.copy()
                ed['uvkey'] = edge_uvkey
            edge_dicts.append(ed)
    return edge_dicts

def get_edge_gdf(graph, attrs: list = None, by_nodes: bool = True, subset: int = None, dicts: bool = False) -> gpd.GeoDataFrame:
    """Collects the edges of a graph to a GeoDataFrame.

    Args:
        attrs: A list of edge attributes that the GeoDataFrame should have as columns.
        by_nodes: A boolean value to indicate whether the edge dictionaries should be extracted as all connections between nodes or just as the
            set of undirected edges in the graph (which is around half of the total number of connections between nodes). 
        subset: The maximum number of rows the GeoDataFrame should have (if None, all rows are returned).
        dicts: A boolean value to specify whether also a list of edge dictionaries should be returned.
    Returns:
        A GeoDataFrame having either all edge attributes as columns or just the ones specified in attrs -argument. 
    """
    edge_dicts = get_all_edge_dicts(graph, attrs=attrs, by_nodes=by_nodes)
    gdf = gpd.GeoDataFrame(edge_dicts, crs=from_epsg(3879))
    if (subset is not None):
        gdf = gdf[:subset]
    if (dicts == True):
        return gdf, edge_dicts
    else:
        return gdf
    
def update_edge_attr_to_graph(graph, edge_df, df_attr: str = None, edge_attr: str = None) -> None:
    """Updates the given edge attribute from a DataFrame to a graph. 

    Args:
        edge_gdf: A GeoDataFrame containing at least columns 'uvkey' and [df_attr]
        df_attr: The name of the column in [edge_df] from which the values for the new edge attribute are read. 
        edge_attr: A name for the edge attribute to which the new attribute values are set.
    """
    for edge in edge_df.itertuples():
        nx.set_edge_attributes(graph, { getattr(edge, 'uvkey'): { edge_attr: getattr(edge, df_attr)}})
