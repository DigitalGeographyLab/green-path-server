"""
This module provides functions for solving the least cost path problem between two points. 

Todo:
    * Try python-igraph library

"""

from typing import List, Set, Dict, Tuple
import time
from shapely.geometry import Point, LineString
from app.graph_handler import GraphHandler
from app.logger import Logger
from utils.igraphs import Edge as E, Node as N

def __get_closest_point_on_line(line: LineString, point: Point) -> Point:
    """Finds the closest point on a line to given point and returns it as Point.
    """
    projected = line.project(point)
    closest_point = line.interpolate(projected)
    return closest_point

def get_nearest_node(log: Logger, G: GraphHandler, point: Point, link_edges: dict = None) -> Dict:
    """Finds (or creates) the nearest node to a given point. 
    If the nearest node is further than the nearest edge to the point, a new node is created
    on the nearest edge on the nearest point on the edge.

    Args:
        G: A GraphHandler instance used in routing.
        point: A location as shapely Point.
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
    nearest_edge = G.find_nearest_edge(point)
    if (nearest_edge is None):
        raise Exception('Nearest edge not found')
    nearest_node = G.find_nearest_node(point)
    start_time = time.time()
    nearest_node_geom = G.get_node_point_geom(nearest_node)
    nearest_edge_point = __get_closest_point_on_line(nearest_edge[E.geometry.value], point)
    # return the nearest node if it is as near (or nearer) as the nearest edge (i.e. at the end of an edge)
    if (nearest_edge_point.distance(nearest_node_geom) < 1 or nearest_node_geom.distance(point) < nearest_edge[E.geometry.value].distance(point)):
        return { 'node': nearest_node, 'offset': round(nearest_node_geom.distance(point), 1), 'add_links': False }
    # check if the nearest edge of the destination is one of the linking edges created for origin 
    if (link_edges is not None):
        if (nearest_edge_point.distance(link_edges['link1'][E.geometry.value]) < 0.2):
            nearest_edge = link_edges['link1']
        if (nearest_edge_point.distance(link_edges['link2'][E.geometry.value]) < 0.2):
            nearest_edge = link_edges['link2']
    # create a new node on the nearest edge to the graph
    new_node = G.add_new_node_to_graph(nearest_edge_point)
    # new edges from the new node to existing nodes need to be created to the graph
    # hence return the geometry of the nearest edge and the nearest point on the nearest edge
    links_to = { 'nearest_edge': nearest_edge, 'nearest_edge_point': nearest_edge_point }
    log.duration(start_time, 'got geoms for adding node & links', unit='ms')
    return { 'node': new_node, 'offset': round(nearest_edge_point.distance(point), 1), 'add_links': True, **links_to }

def get_orig_dest_nodes_and_linking_edges(log: Logger, G: GraphHandler, orig_point: Point, dest_point: Point, aq_sens: List[float], noise_sens: List[float], db_costs: Dict[int,float]):
    """Finds the nearest nodes to origin and destination as well as the newly created edges that connect 
    the origin and destination nodes to the graph.

    Args:
        G: A GraphHandler instance used in routing.
        orig_point: An origin location as shapely Point.
        dest_point: A destination location shapely Point.
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
        orig_node = get_nearest_node(log, G, orig_point)
        # add linking edges to graph if new node was created on the nearest edge
        if (orig_node is not None and orig_node['add_links'] == True):
            orig_link_edges = G.create_linking_edges_for_new_node(
                orig_node['node'], orig_node['nearest_edge_point'], orig_node['nearest_edge'], aq_sens, noise_sens, db_costs)
    except Exception:
        raise Exception('Could not find origin')
    try:
        dest_node = get_nearest_node(log, G, dest_point, link_edges=orig_link_edges)
        # add linking edges to graph if new node was created on the nearest edge
        if (dest_node is not None and dest_node['add_links'] == True):
            dest_link_edges = G.create_linking_edges_for_new_node(
                dest_node['node'], dest_node['nearest_edge_point'], dest_node['nearest_edge'], aq_sens, noise_sens, db_costs)
    except Exception:
        raise Exception('Could not find destination')

    return orig_node, dest_node, orig_link_edges, dest_link_edges
