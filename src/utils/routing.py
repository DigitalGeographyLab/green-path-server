from typing import List, Set, Dict, Tuple, Optional
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import time
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, MultiLineString, box
from shapely.ops import nearest_points
import utils.graphs as graph_utils
import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps
import utils.utils as utils
import utils.quiet_paths as qp

def find_nearest_edge(xy: Dict[str, float], edge_gdf) -> Dict:
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
    edges_sind = edge_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    for radius in [80, 150, 250, 350, 650]:
        possible_matches_index = list(edges_sind.intersection(point_geom.buffer(radius).bounds))
        if (len(possible_matches_index) > 0):
            possible_matches = edge_gdf.iloc[possible_matches_index].copy()
            possible_matches['distance'] = [geom.distance(point_geom) for geom in possible_matches['geometry']]
            shortest_dist = possible_matches['distance'].min()
            if (shortest_dist < (radius - 50) or len(possible_matches_index) > 20):
                break
    if (len(possible_matches_index) == 0):
        print('no near edges found')
        return None
    nearest = possible_matches['distance'] == shortest_dist
    nearest_edges =  possible_matches.loc[nearest]
    nearest_edge = nearest_edges.iloc[0]
    nearest_edge_dict = nearest_edge.to_dict()
    # utils.print_duration(start_time, 'found nearest edge')
    return nearest_edge_dict

def find_nearest_node(xy: Dict[str, float], node_gdf) -> int:
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
    # start_time = time.time()
    nodes_sind = node_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    possible_matches_index = list(nodes_sind.intersection(point_geom.buffer(700).bounds))
    possible_matches = node_gdf.iloc[possible_matches_index]
    points_union = possible_matches.geometry.unary_union
    nearest_geom = nearest_points(point_geom, points_union)[1]
    nearest = possible_matches.geometry.geom_equals(nearest_geom)
    nearest_point =  possible_matches.loc[nearest]
    nearest_node = nearest_point.index.tolist()[0]
    # utils.print_duration(start_time, 'found nearest node')
    return nearest_node

def get_nearest_node(graph, xy: Dict[str, float], edge_gdf, node_gdf, link_edges: dict = None, logging=False) -> Dict:
    """Finds (or creates) the nearest node to a given point. 
    If the nearest node is further than the nearest edge to the point, a new node is created
    on the nearest edge on the nearest point on the edge.

    Args:
        graph: A NetworkX graph used in routing.
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
    coords = geom_utils.get_coords_from_xy(xy)
    point = Point(coords)
    nearest_edge = find_nearest_edge(xy, edge_gdf)
    if (nearest_edge is None):
        return None
    nearest_node = find_nearest_node(xy, node_gdf)
    nearest_node_geom = geom_utils.get_point_from_xy(graph.nodes[nearest_node])
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
    new_node = graph_utils.add_new_node_to_graph(graph, nearest_edge_point, logging=logging)
    # new edges from the new node to existing nodes need to be created to the graph
    # hence return the geometry of the nearest edge and nearest point on nearest edge
    links_to = { 'nearest_edge': nearest_edge, 'nearest_edge_point': nearest_edge_point }
    return { 'node': new_node, 'offset': round(nearest_edge_point.distance(point), 1), 'add_links': True, **links_to }

def get_orig_dest_nodes_and_linking_edges(graph, from_xy: dict, to_xy: dict, edge_gdf, node_gdf, nts: List[float], db_costs: Dict[int,float]):
    """Finds the nearest nodes to origin and destination as well as the newly created egdes that connect 
    the origin and destination nodes to the graph.

    Args:
        graph: A NetworkX graph to be used in routing.
        from_xy: An origin location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        to_xy: A destination location as xy coordinates, e.g. { 'x': 6500, 'y': 2000 }.
        edge_gdf: A GeoDataFrame containing edges of the graph (and line geometries).
        node_gdf: A GeoDataFrame containing nodes of the graph (and point geometries).
        nts: A list of noise tolerance values.
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
    # find/create origin node
    orig_node = get_nearest_node(graph, from_xy, edge_gdf, node_gdf)
    # add linking edges to graph if new node was created on the nearest edge
    if (orig_node is not None and orig_node['add_links'] == True):
        orig_link_edges = graph_utils.create_linking_edges_for_new_node(graph, orig_node['node'], orig_node['nearest_edge_point'], orig_node['nearest_edge'], nts, db_costs)
    # find/create destination node
    dest_node = get_nearest_node(graph, to_xy, edge_gdf, node_gdf, link_edges=orig_link_edges)
    # add linking edges to graph if new node was created on the nearest edge
    if (dest_node is not None and dest_node['add_links'] == True):
        dest_link_edges = graph_utils.create_linking_edges_for_new_node(graph, dest_node['node'], dest_node['nearest_edge_point'], dest_node['nearest_edge'], nts, db_costs)
    return orig_node, dest_node, orig_link_edges, dest_link_edges

def get_shortest_path(graph, orig_node: int, dest_node: int, weight: str = 'length') -> List[int]:
    """Calculates the least cost path by given weight with NetworX library.

    Args:
        graph: A NetworkX graph with which to solve the least cost path optimization problem.
        orig_node: The name of the origin node (number).
        dest_node: The name of the destination node (number).
        weight: The name of the edge attribute to use as cost in the least cost path optimization.
    Returns:
        The least cost path as the sequence of nodes (node ids).
        None is returned if origin and destination nodes are the same or no path is found between them.
    """
    if (orig_node != dest_node):
        try:
            s_path = nx.shortest_path(G=graph, source=orig_node, target=dest_node, weight=weight)
            return s_path
        except:
            print('Could not find paths')
            return None
    else:
        return None
