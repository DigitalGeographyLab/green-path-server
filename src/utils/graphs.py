"""
This module provides various functions for using and manipulating graphs in route optimization.
Most of the functions are utilities for a route planner application that solves the least cost path problem
with adjusted edge weights and subsequently aggregates path level attributes from edge attributes.

Todo:
    * Add support for using other edge weights than noise (e.g. AQI)
    * Try python-igraph library

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

def get_missing_edge_geometries(graph, edge_dict: dict) -> dict:
    """Adds a straight line geometry (LineString) to edge dictionary if the geometry is missing.
    
    Returns:
        A dictionary of the edge (e.g. { 'uvkey': (1,2), 'geometry': LineString_object, ... }).
    """
    edge_d = {}
    edge_d['uvkey'] = edge_dict['uvkey']
    if ('geometry' not in edge_dict):
        node_from = edge_dict['uvkey'][0]
        node_to = edge_dict['uvkey'][1]
        # interpolate missing geometry as straight line between nodes
        edge_geom = get_edge_geom_from_node_pair(graph, node_from, node_to)
        edge_d['geometry'] = edge_geom
    else:
        edge_d['geometry'] = edge_dict['geometry']
    edge_d['length'] = round(edge_d['geometry'].length, 3)
    return edge_d

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

def get_node_gdf(graph) -> gpd.GeoDataFrame:
    """Collects and returns the nodes of a graph as a GeoDataFrame. 
    Names/ids of the nodes are the row ids in the GeoDataFrame.
    """
    nodes, data = zip(*graph.nodes(data=True))
    gdf_nodes = gpd.GeoDataFrame(list(data), index=nodes)
    gdf_nodes['geometry'] = gdf_nodes.apply(lambda row: Point(row['x'], row['y']), axis=1)
    gdf_nodes.crs = graph.graph['crs']
    gdf_nodes.gdf_name = '{}_nodes'.format(graph.graph['name'])
    return gdf_nodes[['geometry']]

def get_node_point_geom(graph, node: int) -> Point:
    node_d = graph.nodes[node]
    return Point(node_d['x'], node_d['y'])

def get_edge_geom_from_node_pair(graph, node_1: int, node_2: int) -> LineString:
    """Returns a straight line edge geometry between two nodes.
    """
    node_1_geom = geom_utils.get_point_from_xy(graph.nodes[node_1])
    node_2_geom = geom_utils.get_point_from_xy(graph.nodes[node_2])
    edge_line = LineString([node_1_geom, node_2_geom])
    return edge_line

def get_new_node_id(graph) -> int:
    """Returns an unique node id that can be used in creating a new node to a graph.
    """
    graph_nodes = graph.nodes
    return  max(graph_nodes)+1

def get_new_node_attrs(graph, point: Point) -> dict:
    """Returns the basic attributes for a new node based on a specified location (Point).
    """
    new_node_id = get_new_node_id(graph)
    wgs_point = geom_utils.project_geom(point, from_epsg=3879, to_epsg=4326)
    geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
    return { 'id': new_node_id, **geom_attrs }

def add_new_node_to_graph(graph, point: Point, debug=True) -> int:
    """Adds a new node to a graph at a specified location (Point) and returns the id of the new node.
    """
    attrs = get_new_node_attrs(graph, point)
    if (debug == True):
        print('add new node:', attrs['id'])
    graph.add_node(attrs['id'], ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
    return attrs['id']

def split_link_edge_geoms(graph, edge_geom: LineString, split_point: Point, node_from: int, node_to: int) -> Tuple[LineString]:
    """Splits the line geometry of an edge to two parts at the location of a new node. Split parts can subsequently be used as linking edges 
    that connect the new node to the graph.

    Returns:
        Tuple containing the geometries of the link edges (LineString, LineString).
    """
    node_from_p = get_node_point_geom(graph, node_from)
    node_to_p = get_node_point_geom(graph, node_to)
    edge_first_p = Point(edge_geom.coords[0])
    # split edge at new node to two line geometries
    split_lines = geom_utils.split_line_at_point(edge_geom, split_point)
    if(edge_first_p.distance(node_from_p) < edge_first_p.distance(node_to_p)):
        link1 = split_lines[0]
        link2 = split_lines[1]
    else:
        link1 = split_lines[1]
        link2 = split_lines[0]
    return link1, link2
    
def create_linking_edges_for_new_node(graph, new_node: int, split_point: Point, edge: dict, sens: list, db_costs: dict, debug=False) -> dict:
    """Creates new edges from a new node that connect the node to the existing nodes in the graph. Also estimates and sets the edge cost attributes
    for the new edges based on attributes of the original edge on which the new node was added. 

    Returns:
        A dictionary containing the following keys:
        node_from: int
        new_node: int
        node_to: int
        link1_d: A dict cotaining the basic edge attributes of the first new linking edge.
        link2_d: A dict cotaining the basic edge attributes of the second new linking edge.
    """
    start_time = time.time()
    node_from = edge['uvkey'][0]
    node_to = edge['uvkey'][1]
    link1, link2 = split_link_edge_geoms(graph, edge['geometry'], split_point, node_from, node_to)

    # interpolate noise cost attributes for new linking edges so that they work in quiet path routing
    link1_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link1)
    link2_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link2)
    # combine link attributes to prepare adding them as new edges
    link1_attrs = { 'geometry': link1, 'length' : round(link1.length, 3), **link1_cost_attrs, 'updatetime': edge['updatetime'] }
    link2_attrs = { 'geometry': link2, 'length' : round(link2.length, 3), **link2_cost_attrs, 'updatetime': edge['updatetime'] }
    # add linking edges with noise cost attributes to graph
    graph.add_edges_from([ (node_from, new_node, { 'uvkey': (node_from, new_node), **link1_attrs }) ])
    graph.add_edges_from([ (new_node, node_from, { 'uvkey': (new_node, node_from), **link1_attrs }) ])
    graph.add_edges_from([ (node_to, new_node, { 'uvkey': (node_to, new_node), **link2_attrs }) ])
    graph.add_edges_from([ (new_node, node_to, { 'uvkey': (new_node, node_to), **link2_attrs }) ])
    link1_d = { 'uvkey': (new_node, node_from), **link1_attrs }
    link2_d = { 'uvkey': (node_to, new_node), **link2_attrs }
    if (debug == True): utils.print_duration(start_time, 'added links for new node', unit='ms')
    return { 'node_from': node_from, 'new_node': new_node, 'node_to': node_to, 'link1': link1_d, 'link2': link2_d }

def remove_new_node_and_link_edges(graph, new_node: dict = None, link_edges: dict = None) -> None:
    """Removes linking edges from a graph. Useful after routing in order to keep the graph unchanged.
    """
    if (link_edges is not None):
        removed_count = 0
        removed_node = False
        rm_edges = [
            (link_edges['node_from'], link_edges['new_node']),
            (link_edges['new_node'], link_edges['node_from']),
            (link_edges['new_node'], link_edges['node_to']),
            (link_edges['node_to'], link_edges['new_node'])
            ]
        for rm_edge in rm_edges:
            try:
                graph.remove_edge(*rm_edge)
                removed_count += 1
            except Exception:
                continue
        try:
            graph.remove_node(new_node['node'])
            removed_node = True
        except Exception:
            pass
        if (removed_count == 0): print('Could not remove linking edges')
        if (removed_node == False): print('Could not remove new node')

def get_least_cost_edge(edges: List[dict], cost_attr: str) -> dict:
    """Returns the least cost edge from a set of edges (dicts) by an edge cost attribute.
    """
    if (len(edges) == 1):
        return next(iter(edges.values()))
    s_edge = next(iter(edges.values()))
    for edge_k in edges.keys():
        if (cost_attr in edges[edge_k].keys() and cost_attr in s_edge.keys()):
            if (edges[edge_k][cost_attr] < s_edge[cost_attr]):
                s_edge = edges[edge_k]
    return s_edge

def get_ordered_edge_line_coords(graph, node_from: int, edge: dict) -> List[tuple]:
    """Returns the coordinates of the line geometry of an edge. The list of coordinates is ordered so that the 
    first point is at the same location as [node_from]. 
    """
    from_point = geom_utils.get_point_from_xy(graph.nodes[node_from])
    edge_line = edge['geometry']
    edge_coords = edge_line.coords
    first_point = Point(edge_coords[0])
    last_point = Point(edge_coords[len(edge_coords)-1])
    if(from_point.distance(first_point) > from_point.distance(last_point)):
        return edge_coords[::-1]
    return edge_coords

def get_edges_from_nodelist(graph, path: List[int], cost_attr: str) -> List[dict]:
    """Loads edges from graph by ordered list of nodes representing a path.
    Loads edge attributes 'cost_update_time', 'length', 'noises', 'dBrange' and 'coords'.
    """
    path_edges = []
    for idx in range(0, len(path)):
        if (idx == len(path)-1):
            break
        edge_d = {}
        node_1 = path[idx]
        node_2 = path[idx+1]
        edges = graph[node_1][node_2]
        edge = get_least_cost_edge(edges, cost_attr)
        edge_d['cost_update_time'] = edge['updatetime'] if ('updatetime' in edge) else {}
        edge_d['length'] = edge['length'] if ('length' in edge) else 0.0
        edge_d['noises'] = edge['noises'] if ('noises' in edge) else {}
        mdB = noise_exps.get_mean_noise_level(edge_d['noises'], edge_d['length'])
        edge_d['dBrange'] = noise_exps.get_noise_range(mdB)
        edge_d['coords'] = get_ordered_edge_line_coords(graph, node_1, edge) if 'geometry' in edge else []
        path_edges.append(edge_d)
    return path_edges

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

def set_graph_noise_costs(graph, edge_gdf, db_costs: dict = None, sens: List[float] = None) -> None:
    """Updates all noise cost attributes to a graph.

    Args:
        db_cost: A dictionary containing the dB-specific noise cost coefficients.
        sens: A list of sensitivity values.
        edge_gdf: A GeoDataFrame containing at least columns 'uvkey' (tuple) and 'noises' (dict).
    """
    edge_nc_gdf = edge_gdf.copy()
    for sen in sens:
        edge_nc_gdf['noise_cost'] = [noise_exps.get_noise_cost(noises=noises, db_costs=db_costs, sen=sen) for noises in edge_nc_gdf['noises']]
        edge_nc_gdf['tot_cost'] = edge_nc_gdf.apply(lambda row: round(row['length'] + row['noise_cost'], 2), axis=1)
        cost_attr = 'nc_'+str(sen)
        update_edge_attr_to_graph(graph, edge_nc_gdf, df_attr='tot_cost', edge_attr=cost_attr)
    
    # set update time as edge attribute
    edge_gdf['updatetime'] =  datetime.now().strftime("%H:%M:%S")
    update_edge_attr_to_graph(graph, edge_gdf, df_attr='updatetime', edge_attr='updatetime')
