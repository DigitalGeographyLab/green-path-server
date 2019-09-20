import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
import ast
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, MultiLineString, box
import utils.exposures as exps
import utils.geometry as geom_utils
import utils.utils as utils

def get_walkable_network(extent_poly_wgs=None):
    # define filter for acquiring walkable street network
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

def get_unwalkable_network(extent_poly_wgs=None):
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

def delete_unused_edge_attrs(graph, save_attrs=['uvkey', 'length', 'geometry', 'noises']):
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

def get_missing_edge_geometries(graph, edge_dict):
    edge_d = {}
    edge_d['uvkey'] = edge_dict['uvkey']
    if ('geometry' not in edge_dict):
        node_from = edge_dict['uvkey'][0]
        node_to = edge_dict['uvkey'][1]
        # interpolate missing geometry as straigth line between nodes
        edge_geom = get_edge_geom_from_node_pair(graph, node_from, node_to)
        edge_d['geometry'] = edge_geom
    else:
        edge_d['geometry'] = edge_dict['geometry']
    edge_d['length'] = round(edge_d['geometry'].length, 3)
    return edge_d

def add_missing_edge_geometries(graph, edge_dicts):
    edge_count = len(edge_dicts)
    for idx, edge_d in enumerate(edge_dicts):
        if ('geometry' not in edge_d):
            node_from = edge_d['uvkey'][0]
            node_to = edge_d['uvkey'][1]
            # interpolate missing geometry as straigth line between nodes
            edge_geom = get_edge_geom_from_node_pair(graph, node_from, node_to)
            # set geometry attribute of the edge
            nx.set_edge_attributes(graph, { edge_d['uvkey']: {'geometry': edge_geom} })
        # set length attribute
        nx.set_edge_attributes(graph, { edge_d['uvkey']: {'length': round(edge_d['geometry'].length, 3)} })
        utils.print_progress(idx+1, edge_count, percentages=True)
    print('\nEdge geometries & lengths set.')

def osmid_to_string(osmid):
    if isinstance(osmid, list):
        osm_str = ''
        osmid_list = sorted(osmid)
        for osm_id in osmid_list:
            osm_str += str(osm_id)+'_'
    else:
        osm_str = str(osmid)
    return osm_str

def export_nodes_edges_to_files(graph):
    nodes, edges = ox.graph_to_gdfs(graph, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
    edges = edges[['geometry', 'u', 'v', 'length']]
    edges.to_file('data/networks.gpkg', layer='koskela_edges', driver="GPKG")
    nodes.to_file('data/networks.gpkg', layer='koskela_nodes', driver="GPKG")

def get_node_gdf(graph):
    node_gdf = ox.graph_to_gdfs(graph, nodes=True, edges=False, node_geometry=True, fill_edge_geometry=False)
    return node_gdf[['geometry']]

def get_node_geom(graph, node):
    node_d = graph.node[node]
    return Point(node_d['x'], node_d['y'])

def get_edge_geom_from_node_pair(graph, node_1, node_2):
    node_1_geom = geom_utils.get_point_from_xy(graph.nodes[node_1])
    node_2_geom = geom_utils.get_point_from_xy(graph.nodes[node_2])
    edge_line = LineString([node_1_geom, node_2_geom])
    return edge_line

def get_new_node_id(graph):
    graph_nodes = graph.nodes
    return  max(graph_nodes)+1

def get_new_node_attrs(graph, point):
    new_node_id = get_new_node_id(graph)
    wgs_point = geom_utils.project_to_wgs(point)
    geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
    return { 'id': new_node_id, **geom_attrs }

def add_new_node_to_graph(graph, point, logging=True):
    attrs = get_new_node_attrs(graph, point)
    if (logging == True):
        print('add new node:', attrs['id'])
    graph.add_node(attrs['id'], ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
    return attrs['id']

def interpolate_link_noises(link_geom, edge_geom, edge_noises):
    link_noises = {}
    link_len_ratio = link_geom.length / edge_geom.length
    for db in edge_noises.keys():
        link_noises[db] = round(edge_noises[db] * link_len_ratio, 3)
    return link_noises

def get_edge_noise_cost_attrs(nts, db_costs, edge_d, link_geom):
    cost_attrs = {}
    # estimate link noises based on link length - edge length -ratio and edge noises
    cost_attrs['noises'] = interpolate_link_noises(link_geom, edge_d['geometry'], edge_d['noises'])
    # calculate noise tolerance specific noise costs
    for nt in nts:
        noise_cost = exps.get_noise_cost(noises=cost_attrs['noises'], db_costs=db_costs, nt=nt)
        cost_attrs['nc_'+str(nt)] = round(noise_cost + link_geom.length, 2)
    noises_sum_len = exps.get_total_noises_len(cost_attrs['noises'])
    if ((noises_sum_len - link_geom.length) > 0.1):
        print('link length unmatch:', noises_sum_len, link_geom.length)
    return cost_attrs

def add_linking_edges_for_new_node(graph, new_node, split_point, edge, nts, db_costs, logging=False):
    edge_geom = edge['geometry']
    # split edge at new node to two line geometries
    split_lines = geom_utils.split_line_at_point(edge_geom, split_point)
    node_from = edge['uvkey'][0]
    node_to = edge['uvkey'][1]
    node_from_p = get_node_geom(graph, node_from)
    node_to_p = get_node_geom(graph, node_to)
    edge_first_p = Point(edge_geom.coords[0])
    if(edge_first_p.distance(node_from_p) < edge_first_p.distance(node_to_p)):
        link1 = split_lines[0]
        link2 = split_lines[1]
    else:
        link1 = split_lines[1]
        link2 = split_lines[0]
    if (logging == True):
        print('add linking edges between:', node_from, new_node, node_to)
    # interpolate noise cost attributes for new linking edges so that they work in quiet path routing
    link1_noise_costs = get_edge_noise_cost_attrs(nts, db_costs, edge, link1)
    link2_noise_costs = get_edge_noise_cost_attrs(nts, db_costs, edge, link2)
    # combine link attributes to prepare adding them as new edges
    link1_attrs = { 'geometry': link1, 'length' : round(link1.length, 3), **link1_noise_costs }
    link2_attrs = { 'geometry': link2, 'length' : round(link2.length, 3), **link2_noise_costs }
    # add linking edges with noice cost attributes to graph
    graph.add_edges_from([ (node_from, new_node, { 'uvkey': (node_from, new_node), **link1_attrs }) ])
    graph.add_edges_from([ (new_node, node_from, { 'uvkey': (new_node, node_from), **link1_attrs }) ])
    graph.add_edges_from([ (node_to, new_node, { 'uvkey': (node_to, new_node), **link2_attrs }) ])
    graph.add_edges_from([ (new_node, node_to, { 'uvkey': (new_node, node_to), **link2_attrs }) ])
    link1_d = { 'uvkey': (new_node, node_from), **link1_attrs }
    link2_d = { 'uvkey': (node_to, new_node), **link2_attrs }
    return { 'node_from': node_from, 'new_node': new_node, 'node_to': node_to, 'link1': link1_d, 'link2': link2_d }

def remove_new_node_and_link_edges(graph, new_node_d):
    if ('link_edges' in new_node_d.keys()):
        link_edges = new_node_d['link_edges']
        edges = [
            (link_edges['node_from'], link_edges['new_node']),
            (link_edges['new_node'], link_edges['node_from']),
            (link_edges['new_node'], link_edges['node_to']),
            (link_edges['node_to'], link_edges['new_node'])
            ]
        for edge in edges:
            try:
                graph.remove_edge(*edge)
            except Exception:
                continue
        try:
            graph.remove_node(link_edges['new_node'])
        except Exception:
            pass

def get_shortest_edge(edges, weight):
    if (len(edges) == 1):
        return next(iter(edges.values()))
    s_edge = next(iter(edges.values()))
    for edge_k in edges.keys():
        if (weight in edges[edge_k].keys() and weight in s_edge.keys()):
            if (edges[edge_k][weight] < s_edge[weight]):
                s_edge = edges[edge_k]
    return s_edge

def get_edge_line_coords(graph, node_from, edge_d):
    from_point = geom_utils.get_point_from_xy(graph.nodes[node_from])
    edge_line = edge_d['geometry']
    edge_coords = edge_line.coords
    first_point = Point(edge_coords[0])
    last_point = Point(edge_coords[len(edge_coords)-1])
    if(from_point.distance(first_point) > from_point.distance(last_point)):
        return edge_coords[::-1]
    return edge_coords

def aggregate_path_geoms_attrs(graph, path, weight='length', geom=True, noises=False):
    result = {}
    edge_lengths = []
    path_coords = []
    edge_exps = []
    for idx in range(0, len(path)):
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edges = graph[node_1][node_2]
        edge_d = get_shortest_edge(edges, weight)
        if geom:
            if ('nc_0.1') not in edge_d:
                print('missing noise cost attr')
            if ('geometry' in edge_d):
                edge_lengths.append(edge_d['length'])
                edge_coords = get_edge_line_coords(graph, node_1, edge_d)
            else:
                edge_line = get_edge_geom_from_node_pair(graph, node_1, node_2)
                edge_lengths.append(edge_line.length)
                edge_coords = edge_line.coords
            path_coords += edge_coords
            edge_noise_len_diff = (edge_d['length'] - exps.get_total_noises_len(edge_d['noises']))
            if (edge_noise_len_diff < -0.05):
                print('idx:', idx, 'from:', node_1, 'to:', node_2)
                print(' problems with edge:', edge_d['uvkey'], edge_d['noises'])
                print(' edge lens vs noise lens:', edge_d['length'], exps.get_total_noises_len(edge_d['noises']))
        if noises:
            if ('noises' in edge_d):
                edge_exps.append(edge_d['noises'])
    if geom:
        path_line = LineString(path_coords)
        total_length = round(sum(edge_lengths),2)
        result['geometry'] = path_line
        result['total_length'] = total_length
    if noises:
        result['noises'] = exps.aggregate_exposures(edge_exps)
    return result

def get_all_edge_dicts(graph, attrs=None, by_nodes=True):
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
        return edge_dicts
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

def get_edge_gdf(graph, attrs=None, by_nodes=True, subset=None, dicts=False):
    edge_dicts = get_all_edge_dicts(graph, attrs=attrs, by_nodes=by_nodes)
    gdf = gpd.GeoDataFrame(edge_dicts, crs=from_epsg(3879))
    if (subset is not None):
        gdf = gdf[:subset]
    if (dicts == True):
        return gdf, edge_dicts
    else:
        return gdf
    
def update_edge_noises_to_graph(edge_gdf, graph):
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph, { getattr(edge, 'uvkey'): { 'noises': getattr(edge, 'noises')}})

def update_edge_costs_to_graph(edge_gdf, graph, nt):
    cost_attr = 'nc_'+str(nt)
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph, { getattr(edge, 'uvkey'): { cost_attr: getattr(edge, 'tot_cost')}}) 

def set_graph_noise_costs(graph, edge_gdf, db_costs=None, nts=None):
    edge_nc_gdf = edge_gdf.copy()
    for nt in nts:
        edge_nc_gdf['noise_cost'] = [exps.get_noise_cost(noises=noises, db_costs=db_costs, nt=nt) for noises in edge_nc_gdf['noises']]
        edge_nc_gdf['tot_cost'] = edge_nc_gdf.apply(lambda row: round(row['length'] + row['noise_cost'], 2), axis=1)
        update_edge_costs_to_graph(edge_nc_gdf, graph, nt)
