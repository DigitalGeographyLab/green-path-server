from enum import Enum
from typing import List, Set, Dict, Tuple
import geopandas as gpd
import igraph as ig
from pyproj import CRS
from utils.schema import Node, Edge, edge_attr_converters, node_attr_converters
from utils.logger import Logger

def get_edge_dicts(G: ig.Graph, attrs: List[Enum] = [Edge.geometry]) -> list:
    """Returns list of all edges of a graph as dictionaries with the specified attributes. 
    """
    edge_dicts = []
    for edge in G.es:
        edge_attrs = edge.attributes()
        edge_dict = {}
        for attr in attrs:
            if (attr.value in edge_attrs):
                edge_dict[attr.name] = edge_attrs[attr.value]
        edge_dicts.append(edge_dict)
    return edge_dicts

def get_edge_gdf(G: ig.Graph, id_attr: Enum = None, attrs: List[Enum] = [], ig_attrs: List[str] = [], geom_attr: Enum = Edge.geometry, epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns edges of a graph as pandas GeoDataFrame. 
    """
    edge_dicts = []
    ids = []
    for edge in G.es:
        edge_dict = {}
        edge_attrs = edge.attributes()
        ids.append(edge_attrs[id_attr.value] if id_attr is not None else edge.index)
        edge_dict[geom_attr.name] = edge_attrs[geom_attr.value]
        for attr in attrs:
            if (attr.value in edge_attrs):
                edge_dict[attr.name] = edge_attrs[attr.value]
        for attr in ig_attrs:
            if (hasattr(edge, attr)):
                edge_dict[attr] = getattr(edge, attr)
        edge_dicts.append(edge_dict)

    return gpd.GeoDataFrame(edge_dicts, index=ids, crs=CRS.from_epsg(epsg))

def get_node_gdf(G: ig.Graph, id_attr: Enum = None, attrs: List[Enum] = [], ig_attrs: List[str] = [], geom_attr: Enum = Node.geometry, epsg: int = 3879) -> gpd.GeoDataFrame:
    """Returns nodes of a graph as pandas GeoDataFrame. 
    """
    node_dicts = []
    ids = []
    for node in G.vs:
        node_dict = {}
        node_attrs = node.attributes()
        ids.append(node_attrs[id_attr.value] if id_attr is not None else node.index)
        node_dict[geom_attr.name] = node_attrs[geom_attr.value]
        for attr in attrs:
            if(attr.value in node_attrs):
                node_dict[attr.name] = node_attrs[attr.value]
        for attr in ig_attrs:
            if (hasattr(node, attr)):
                node_dict[attr] = getattr(node, attr)
        node_dicts.append(node_dict)

    return gpd.GeoDataFrame(node_dicts, index=ids, crs=CRS.from_epsg(epsg))

def read_graphml(graph_file: str, log: Logger = None) -> ig.Graph:
    G = ig.Graph()
    G = G.Read_GraphML(graph_file)
    del(G.vs['id'])
    for attr in G.vs[0].attributes():
        try:
            converter = node_attr_converters[Node(attr)]
            G.vs[attr] = [converter(value) for value in list(G.vs[attr])]
        except Exception:
            if (log is not None): log.warning(f'failed to read node attribute {attr}')
    for attr in G.es[0].attributes():
        try:
            converter = edge_attr_converters[Edge(attr)]
            G.es[attr] = [converter(value) for value in list(G.es[attr])]
        except Exception:
            if (log is not None): log.warning(f'failed to read edge attribute {attr}')
    return G

def export_to_graphml(G: ig.Graph, graph_file: str, n_attrs=[], e_attrs=[]):
    Gc = G.copy()
    if (n_attrs == []):
        for attr in Node:
            if (attr.value in Gc.vs[0].attributes()):
                Gc.vs[attr.value] = [str(value) for value in list(Gc.vs[attr.value])]
    else:
        for attr in n_attrs:
            Gc.vs[attr.value] = [str(value) for value in list(Gc.vs[attr.value])]
        # delete unspecified attributes
        for node_attr in G.vs.attribute_names():
            if (node_attr not in [attr.value for attr in n_attrs]):
                del(Gc.vs[node_attr])
    if (e_attrs == []):
        for attr in Edge:
            if (attr.value in Gc.es[0].attributes()):
                Gc.es[attr.value] = [str(value) for value in list(Gc.es[attr.value])]
    else:
        for attr in e_attrs:
            Gc.es[attr.value] = [str(value) for value in list(Gc.es[attr.value])]
        # delete unspecified attributes
        for edge_attr in G.es.attribute_names():
            if (edge_attr not in [attr.value for attr in e_attrs]):
                del(Gc.es[edge_attr])

    Gc.save(graph_file, format='graphml')
