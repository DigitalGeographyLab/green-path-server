import ast
from shapely import wkt
from shapely.geometry import Point, LineString
from fiona.crs import from_epsg
import numpy as np
import geopandas as gpd
import igraph as ig
import networkx as nx
import utils.graphs as nx_utils
import utils.files as file_utils

def convert_edge_attr_types(edge: ig.Edge) -> None:
    attrs = edge.attributes()
    edge['edge_id'] = int(attrs['edge_id'])
    edge['uvkey'] = ast.literal_eval(attrs['uvkey'])
    edge['length'] = float(attrs['length'])    
    edge['noises'] = ast.literal_eval(attrs['noises'])
    edge['geometry'] = wkt.loads(attrs['geometry'])

def convert_node_attr_types(N: ig.Vertex) -> None:
    attrs = N.attributes()
    N['vertex_id'] = int(attrs['vertex_id'])
    N['x_coord'] = float(attrs['x_coord'])
    N['y_coord'] = float(attrs['y_coord'])

def set_graph_attributes(G: ig.Graph) -> ig.Graph:
    for edge in G.es:
        convert_edge_attr_types(edge)
    for node in G.vs:
        convert_node_attr_types(node)
    return G

def read_ig_graphml(graph_file: str = 'ig_export_test.graphml') -> ig.Graph:
    G = ig.Graph()
    G = G.Read_GraphML('graphs/' + graph_file)
    return set_graph_attributes(G)

def convert_nx_2_igraph(nx_g: nx.Graph) -> ig.Graph:
    
    # read nodes from nx graph
    nodes, data = zip(*nx_g.nodes(data=True))
    node_df = gpd.GeoDataFrame(list(data), index=nodes)
    node_df['id_ig'] = np.arange(len(node_df))
    node_df['id_nx'] = node_df.index

    ids_nx_ig = {}
    ids_ig_nx = {}

    for node in node_df.itertuples():
        ids_nx_ig[getattr(node, 'id_nx')] = getattr(node, 'id_ig')
        ids_ig_nx[getattr(node, 'id_ig')] = getattr(node, 'id_nx')

    G = ig.Graph()

    # add empty vertices (nodes)
    G.add_vertices(len(node_df))

    # set node/vertex attributes
    G.vs['vertex_id'] = list(node_df['id_ig'])
    G.vs['x_coord'] = list(node_df['x'])
    G.vs['y_coord'] = list(node_df['y'])

    # read edges from nx graph
    def get_ig_uvkey(uvkey):
        return (ids_nx_ig[uvkey[0]], ids_nx_ig[uvkey[1]], uvkey[2])
    edge_gdf = nx_utils.get_edge_gdf(nx_g, by_nodes=False)
    edge_gdf['uvkey_ig'] = [get_ig_uvkey(uvkey) for uvkey in edge_gdf['uvkey']]
    edge_gdf['uv_ig'] = [(uvkey_ig[0], uvkey_ig[1]) for uvkey_ig in edge_gdf['uvkey_ig']]
    edge_gdf['id_ig'] = np.arange(len(edge_gdf))

    # add edges to ig graph
    G.add_edges(list(edge_gdf['uv_ig']))
    G.es['edge_id'] = list(edge_gdf['id_ig'])
    G.es['uvkey'] = list(edge_gdf['uvkey_ig'])
    G.es['length'] = list(edge_gdf['length'])
    G.es['noises'] = list(edge_gdf['noises'])
    G.es['geometry'] = list(edge_gdf['geometry'])

    return G

def save_ig_to_graphml(G: ig.Graph, graph_out: str = 'ig_export_test.graphml'):
    Gc = G.copy()
    # stringify node attributes before exporting to graphml
    Gc.vs['vertex_id'] = [str(vertex_id) for vertex_id in Gc.vs['vertex_id']]
    Gc.vs['x_coord'] = [str(x_coord) for x_coord in Gc.vs['x_coord']]
    Gc.vs['y_coord'] = [str(y_coord) for y_coord in Gc.vs['y_coord']]
    # stringify edge attributes before exporting to graphml
    Gc.es['edge_id'] = [str(edge_id) for edge_id in Gc.es['edge_id']]
    Gc.es['uvkey'] = [str(uvkey) for uvkey in Gc.es['uvkey']]
    Gc.es['length'] = [str(length) for length in Gc.es['length']]
    Gc.es['noises'] = [str(noises) for noises in Gc.es['noises']]
    Gc.es['geometry'] = [str(geometry) for geometry in Gc.es['geometry']]
    Gc.save('graphs/' + graph_out, format='graphml')


def get_edge_dicts(G: ig.Graph, get_attrs: list = ['edge_id', 'uvkey', 'geometry']) -> list:
    edge_dicts = []
    for edge in G.es:
        edge_attrs = edge.attributes()
        edge_dict = {}
        for attr in get_attrs:
            if (attr in edge_attrs):
                edge_dict[attr] = edge_attrs[attr]
                if (edge_dict['edge_id'] != edge.index):
                    print('edge_id and index do not match!')
        edge_dicts.append(edge_dict)
    return edge_dicts

def get_edge_gdf(G: ig.Graph) -> gpd.GeoDataFrame:
    edge_dicts = get_edge_dicts(G)

    ids = [ed['edge_id'] for ed in edge_dicts]
    geometry = [ed['geometry'] for ed in edge_dicts]

    gdf = gpd.GeoDataFrame(geometry=geometry, index=ids, crs=from_epsg(3879))
    print(gdf.head())
    return gdf

def get_node_gdf(G: ig.Graph) -> gpd.GeoDataFrame:
    node_dicts = []
    for node in G.vs:
        node_attrs = node.attributes()
        if (node_attrs['vertex_id'] != node.index):
            print('vertex_id and index do not match!')
        node_dicts.append(node_attrs)

    ids = [nd['vertex_id'] for nd in node_dicts]
    geometry = [Point(nd['x_coord'], nd['y_coord']) for nd in node_dicts]

    gdf = gpd.GeoDataFrame(geometry=geometry, index=ids, crs=from_epsg(3879))
    print(gdf.head())

    return gdf
