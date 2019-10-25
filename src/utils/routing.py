"""
This module provides functions for solving the least cost path problem between two points. 

Todo:
    * Add support for using other edge weights than noise (e.g. AQI)
    * Try python-igraph library

"""

from typing import List, Set, Dict, Tuple
import time
import networkx as nx
from shapely.geometry import Point
from shapely.ops import nearest_points
import utils.graphs as graph_utils
import utils.geometry as geom_utils
import utils.utils as utils
from utils.graph_handler import GraphHandler

def find_nearest_edge(xy: Dict[str, float], edge_gdf, debug=False) -> Dict:
    """Finds the nearest edge to a given point.

    Args:
        xy: A location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        edge_gdf: GeoDataFrame containing edges (and line geometries).
    Note:
        The coordinate systems of both xy and node_gdf should be projected (EPSG:3879).
        The edge_gdf should have spatial index built to make the search quick.
        It's enough to run edges_sind = edge_gdf.sindex once before using this.
    Returns:
        The nearest edge as dictionary, having key-value pairs by the columns of the edge_gdf.
    """
    start_time = time.time()
    edges_sind = edge_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    for radius in [80, 150, 250, 350, 650]:
        possible_matches_index = list(edges_sind.intersection(point_geom.buffer(radius).bounds))
        if (len(possible_matches_index) > 0):
            possible_matches = edge_gdf.iloc[possible_matches_index].copy()
            possible_matches['distance'] = [geom.distance(point_geom) for geom in possible_matches['geometry']]
            shortest_dist = possible_matches['distance'].min()
            if (shortest_dist < radius):
                break
    if (len(possible_matches_index) == 0):
        print('no near edges found')
        return None
    nearest = possible_matches['distance'] == shortest_dist
    nearest_edge_dict =  possible_matches.loc[nearest].iloc[0].to_dict()
    if (debug == True): utils.print_duration(start_time, 'found nearest edge', unit='ms')
    return nearest_edge_dict

def find_nearest_node(xy: Dict[str, float], node_gdf, debug=False) -> int:
    """Finds the nearest node to a given point.

    Args:
        xy: A location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        node_gdf: A GeoDataFrame containing nodes (and point geometries).
    Note:
        The coordinate systems of both xy and node_gdf should be projected (EPSG:3879).
        The node_gdf should have spatial index built to make the search quick.
        It's enough to run nodes_sind = node_gdf.sindex once before using this.
    Returns:
        The name of the nearest node (number).
    """
    start_time = time.time()
    nodes_sind = node_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    for radius in [100, 300, 700]:
        possible_matches_index = list(nodes_sind.intersection(point_geom.buffer(radius).bounds))
        if (len(possible_matches_index) == 0):
            continue
        possible_matches = node_gdf.iloc[possible_matches_index]
        points_union = possible_matches.geometry.unary_union
        nearest_geom = nearest_points(point_geom, points_union)[1]
        nearest = possible_matches.geometry.geom_equals(nearest_geom)
        nearest_point =  possible_matches.loc[nearest]
        nearest_node = nearest_point.index.tolist()[0]
    if (debug == True): utils.print_duration(start_time, 'found nearest node', unit='ms')
    return nearest_node

def get_nearest_node(G: GraphHandler, xy: Dict[str, float], link_edges: dict = None, debug=False) -> Dict:
    """Finds (or creates) the nearest node to a given point. 
    If the nearest node is further than the nearest edge to the point, a new node is created
    on the nearest edge on the nearest point on the edge.

    Args:
        G: A GraphHandler instance used in routing.
        xy: A location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        edge_gdf: A GeoDataFrame containing edges of the graph (and line geometries).
        node_gdf: A GeoDataFrame containing nodes of the graph (and point geometries).
        link_edges: A dictionary that can contain additional edges that were created when connecting
                    the added origin node to existing nodes. 
    Note:
        If the origin and destination nodes are created on the same edge (which rarely happens), some special logic is needed:
        When creating destination node, it needs to be created on one of the linking edges from the origin - not on the nearest
        edge, to get the shortest path right between the nodes.
    Returns:
        A dictionary containing the name of the new nearest node ('node'),
        offset from the given xy location in meters ('offset'),
        boolean variable 'add_links' that indicates whether the nearest node is a newly added node
        and needs to be connected to the graph later by adding new edges to the graph,
        'nearest edge' that contains the attributes of the nearest edge and
        'nearest_edge_point' which is a Shapely Point object located on the nearest point on the nearest edge.
        (The last two objects are needed for creating the linking edges for newly created nodes)
    """
    point = geom_utils.get_point_from_xy(xy)
    nearest_edge = G.find_nearest_edge(point, debug=debug)
    if (nearest_edge is None):
        raise Exception('Nearest edge not found')
    nearest_node = G.find_nearest_node(point, debug=debug)
    start_time = time.time()
    nearest_node_geom = geom_utils.get_point_from_xy(G.graph.nodes[nearest_node])
    nearest_edge_point = geom_utils.get_closest_point_on_line(nearest_edge['geometry'], point)
    # return the nearest node if it is as near (or nearer) as the nearest edge (i.e. at the end of an edge)
    if (nearest_edge_point.distance(nearest_node_geom) < 1 or nearest_node_geom.distance(point) < nearest_edge['geometry'].distance(point)):
        return { 'node': nearest_node, 'offset': round(nearest_node_geom.distance(point), 1), 'add_links': False }
    # check if the nearest edge of the destination is one of the linking edges created for origin 
    if (link_edges is not None):
        if (nearest_edge_point.distance(link_edges['link1']['geometry']) < 0.2):
            nearest_edge = link_edges['link1']
        if (nearest_edge_point.distance(link_edges['link2']['geometry']) < 0.2):
            nearest_edge = link_edges['link2']
    # create a new node on the nearest edge to the graph
    new_node = G.add_new_node_to_graph(nearest_edge_point)
    # new edges from the new node to existing nodes need to be created to the graph
    # hence return the geometry of the nearest edge and the nearest point on the nearest edge
    links_to = { 'nearest_edge': nearest_edge, 'nearest_edge_point': nearest_edge_point }
    if (debug == True): utils.print_duration(start_time, 'got geoms for adding node & links', unit='ms')
    return { 'node': new_node, 'offset': round(nearest_edge_point.distance(point), 1), 'add_links': True, **links_to }

def get_orig_dest_nodes_and_linking_edges(G: GraphHandler, from_xy: dict, to_xy: dict, sens: List[float], db_costs: Dict[int,float], debug=False):
    """Finds the nearest nodes to origin and destination as well as the newly created edges that connect 
    the origin and destination nodes to the graph.

    Args:
        G: A GraphHandler instance used in routing.
        from_xy: An origin location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        to_xy: A destination location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        edge_gdf: A GeoDataFrame containing edges of the graph (and line geometries).
        node_gdf: A GeoDataFrame containing nodes of the graph (and point geometries).
        sens: A list of noise sensitivity values.
        db_costs: A dictionary containing noise cost coefficients.
    Returns:
        orig_node: The name of the origin node (number).
        dest_node: The name of the destination node (number).
        orig_link_edges: The newly created edges (dict) that link the origin node to the graph.
        dest_link_edges: The newly created edges (dict) that link the destination node to the graph.
        If some of these are not found, None is returned respectively.
    """
    orig_link_edges = None
    dest_link_edges = None

    try:
        orig_node = get_nearest_node(G, from_xy, debug=debug)
        # add linking edges to graph if new node was created on the nearest edge
        if (orig_node is not None and orig_node['add_links'] == True):
            orig_link_edges = G.create_linking_edges_for_new_node(
                orig_node['node'], orig_node['nearest_edge_point'], orig_node['nearest_edge'], sens, db_costs, debug=debug)
    except Exception:
        raise Exception('Could not find origin')
    try:
        dest_node = get_nearest_node(G, to_xy, link_edges=orig_link_edges, debug=debug)
        # add linking edges to graph if new node was created on the nearest edge
        if (dest_node is not None and dest_node['add_links'] == True):
            dest_link_edges = G.create_linking_edges_for_new_node(
                dest_node['node'], dest_node['nearest_edge_point'], dest_node['nearest_edge'], sens, db_costs, debug=debug)
    except Exception:
        raise Exception('Could not find destination')

    return orig_node, dest_node, orig_link_edges, dest_link_edges

def get_least_cost_path(G: GraphHandler, orig_node: int, dest_node: int, weight: str = 'length') -> List[int]:
    """Calculates a least cost path by the given edge weight.

    Args:
        G: A GraphHandler instance used in routing.
        orig_node: The name of the origin node (number).
        dest_node: The name of the destination node (number).
        weight: The name of the edge attribute to use as cost in the least cost path optimization.
    Returns:
        The least cost path as a sequence of nodes (node ids).
        Returns None if the origin and destination nodes are the same or no path is found between them.
    """
    if (orig_node != dest_node):
        try:
            s_path = nx.shortest_path(G=G.graph, source=orig_node, target=dest_node, weight=weight)
            return s_path
        except:
            raise Exception('Could not find paths')
    else:
        raise Exception('Origin and destination are the same location')
