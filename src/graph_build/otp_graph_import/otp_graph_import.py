from typing import Union
from graph_build.otp_graph_import.conf import OtpGraphImportConf
from shapely.geometry import Point, LineString
import numpy as np
import pandas as pd
import geopandas as gpd
import igraph as ig
import shapely.wkt
from pyproj import CRS
from common.igraph import Node, Edge
import common.igraph as ig_utils
import common.geometry as geom_utils
import logging


log = logging.getLogger('otp_graph_import')


def convert_otp_graph_to_igraph(
    node_csv_file: str,
    edge_csv_file: str,
    hma_poly_file: str,
    igraph_out_file: str,
    b_export_otp_data_to_gpkg: bool = False,
    b_export_decomposed_igraphs_to_gpkg: bool = False,
    b_export_final_graph_to_gpkg: bool = False,
    debug_otp_graph_gpkg: str = 'debug/otp_graph_features.gpkg',
    debug_igraph_gpkg: str = 'debug/otp2igraph_features.gpkg',
) -> ig.Graph:

    hma_poly = geom_utils.project_geom(gpd.read_file(hma_poly_file)['geometry'][0])

    # 1) read nodes nodes from CSV
    n = pd.read_csv(node_csv_file, sep=';')
    log.info(f'read {len(n.index)} nodes')
    log.debug(f'node column types: {n.dtypes}')
    log.debug(f'nodes head: {n.head()}')
    log.info('creating node gdf')
    n[Node.geometry.name] = [
        shapely.wkt.loads(geom) if isinstance(geom, str) else Point() for geom in n[Node.geometry.name]
    ]
    n[Node.geom_wgs.name] = n[Node.geometry.name]
    n = gpd.GeoDataFrame(n, geometry=Node.geometry.name, crs=CRS.from_epsg(4326))
    log.info('reprojecting nodes to etrs')
    n = n.to_crs(epsg=3879)
    log.debug(f'nodes head: {n.head()}')

    # 2) read edges from CSV
    e = pd.read_csv(edge_csv_file, sep=';')
    log.info(f'read {len(e.index)} edges')
    log.debug(f'edge column types: {e.dtypes}')
    log.debug(f'edges head: {e.head()}')
    log.info('creating edge gdf')
    e[Edge.geometry.name] = [
        shapely.wkt.loads(geom) if isinstance(geom, str) else LineString() for geom in e[Edge.geometry.name]
    ]
    e[Edge.geom_wgs.name] = e[Edge.geometry.name]
    e = gpd.GeoDataFrame(e, geometry=Edge.geometry.name, crs=CRS.from_epsg(4326))
    log.info('reprojecting edges to etrs')
    e = e.to_crs(epsg=3879)
    log.debug(f'edges head: {e.head()}')

    # 3) export graph data to gpkg
    if b_export_otp_data_to_gpkg:
        log.info('writing otp graph data to gpkg')
        e.drop(columns=[Edge.geom_wgs.name]).to_file(debug_otp_graph_gpkg, layer='edges', driver='GPKG')
        log.info(f'exported edges to {debug_otp_graph_gpkg} (layer=edges)')
        n.drop(columns=[Edge.geom_wgs.name]).to_file(debug_otp_graph_gpkg, layer='nodes', driver='GPKG')
        log.info(f'exported nodes to {debug_otp_graph_gpkg} (layer=nodes)')

    # 4) filter out edges that are unsuitable for both walking and cycling
    def filter_df_by_query(df: pd.DataFrame, query: str, name: str = 'rows'):
        count_before = len(df.index)
        df_filt = df.query(query).copy()
        filt_ratio = (count_before-len(df_filt.index)) / count_before
        log.info(f'filtered out {count_before-len(df_filt.index)} {name} ({round(filt_ratio * 100, 1)} %) by {query}')
        return df_filt

    e_filt = filter_df_by_query(e, f'{Edge.allows_walking.name} == True or {Edge.allows_biking.name} == True', name='edges')
    e_filt = filter_df_by_query(e_filt, f'{Edge.is_no_thru_traffic.name} == False', name='edges')

    # 5) create a dictionaries for converting otp ids to ig ids and vice versa
    log.debug('create maps for converting otp ids to ig ids')
    n[Node.id_ig.name] = np.arange(len(n.index))
    ids_otp_ig = {}
    ids_ig_otp = {}
    for node in n.itertuples():
        ids_otp_ig[getattr(node, Node.id_otp.name)] = getattr(node, Node.id_ig.name)
        ids_ig_otp[getattr(node, Node.id_ig.name)] = getattr(node, Node.id_otp.name)

    # 6) add nodes to graph
    log.info('adding nodes to graph')
    G = ig.Graph(directed=True)
    G.add_vertices(len(n.index))
    for attr in Node:
        if attr.name in n.columns:
            G.vs[attr.value] = list(n[attr.name])
        else:
            log.warning(f'node column {attr.name} not present in dataframe')

    # 7) add edges to graph
    log.info('adding edges to graph')

    # get edge lengths by projected geometry
    e_filt[Edge.length.name] = [
        round(geom.length, 4) if isinstance(geom, LineString) else 0.0 for geom in e_filt[Edge.geometry.name]
    ]

    def get_ig_uv(edge):
        return (ids_otp_ig[edge['node_orig_id']], ids_otp_ig[edge['node_dest_id']])

    e_filt['uv_ig'] = e_filt.apply(lambda row: get_ig_uv(row), axis=1)
    e_filt[Edge.id_ig.name] = np.arange(len(e_filt.index))
    G.add_edges(list(e_filt['uv_ig']))
    for attr in Edge:
        if attr.name in e_filt.columns:
            G.es[attr.value] = list(e_filt[attr.name])
        else:
            log.warning(f'edge column {attr.name} not present in dataframe')

    # 8) delete edges outside Helsinki Metropolitan Area (HMA)
    hma_buffered = hma_poly.buffer(100)

    def intersects_hma(geom: Union[LineString, None]):
        if not geom or geom.is_empty:
            return True
        return geom.intersects(hma_buffered)

    e_gdf = ig_utils.get_edge_gdf(G)
    log.info('finding edges that intersect with HMA')
    e_gdf['in_hma'] = [intersects_hma(line) for line in e_gdf[Edge.geometry.name]]
    e_gdf_del = e_gdf.query('in_hma == False').copy()
    out_ratio = round(100 * len(e_gdf_del.index)/len(e_gdf.index), 1)
    log.info(f'found {len(e_gdf_del.index)} ({out_ratio} %) edges outside HMA')

    log.info('deleting edges')
    before_count = G.ecount()
    G.delete_edges(e_gdf_del.index.tolist())
    after_count = G.ecount()
    log.info(f'deleted {before_count-after_count} edges')

    # check if id_ig:s need to be updated to edge attributes
    mismatch_count = len(
        [edge.index for edge in G.es if edge.attributes()[Edge.id_ig.value] != edge.index]
    )
    log.info(f'invalid edge ids: {mismatch_count}')
    # reassign igraph indexes to edge and node attributes
    G.es[Edge.id_ig.value] = [e.index for e in G.es]
    G.vs[Node.id_ig.value] = [v.index for v in G.vs]
    # check if id_ig:s need to be updated to edge attributes
    mismatch_count = len(
        [edge.index for edge in G.es if edge.attributes()[Edge.id_ig.value] != edge.index]
    )
    log.info(f'invalid edge ids: {mismatch_count} (after re-indexing)')

    # 9) find and inspect subgraphs by decomposing the graph
    sub_graphs = G.decompose(mode='STRONG')
    log.info(f'found {len(sub_graphs)} subgraphs')

    graph_sizes = [graph.ecount() for graph in sub_graphs]
    log.info(f'subgraphs with more than 10 edges: {len([s for s in graph_sizes if s > 10])}')
    log.info(f'subgraphs with more than 50 edges: {len([s for s in graph_sizes if s > 50])}')
    log.info(f'subgraphs with more than 100 edges: {len([s for s in graph_sizes if s > 100])}')
    log.info(f'subgraphs with more than 500 edges: {len([s for s in graph_sizes if s > 500])}')
    log.info(f'subgraphs with more than 10000 edges: {len([s for s in graph_sizes if s > 10000])}')

    small_graphs = [graph for graph in sub_graphs if graph.ecount() <= 15]
    medium_graphs = [graph for graph in sub_graphs if (graph.ecount() > 15 and graph.ecount() <= 500)]
    big_graphs = [graph for graph in sub_graphs if graph.ecount() > 500]

    small_graph_edges = []
    for graph_id, graph in enumerate(small_graphs):
        edges = ig_utils.get_edge_dicts(graph, attrs=[Edge.id_otp, Edge.id_ig, Edge.geometry])
        for edge in edges:
            edge['graph_id'] = graph_id
        small_graph_edges.extend(edges)

    medium_graph_edges = []
    for graph_id, graph in enumerate(medium_graphs):
        edges = ig_utils.get_edge_dicts(graph, attrs=[Edge.id_otp, Edge.id_ig, Edge.geometry])
        for edge in edges:
            edge['graph_id'] = graph_id
        medium_graph_edges.extend(edges)

    big_graph_edges = []
    for graph_id, graph in enumerate(big_graphs):
        edges = ig_utils.get_edge_dicts(graph, attrs=[Edge.id_otp, Edge.id_ig, Edge.geometry])
        for edge in edges:
            edge['graph_id'] = graph_id
        big_graph_edges.extend(edges)

    if b_export_decomposed_igraphs_to_gpkg:
        log.info('exporting subgraphs to gpkg')
        # graphs with <= 15 edges
        small_graph_edges_gdf = gpd.GeoDataFrame(small_graph_edges, crs=CRS.from_epsg(3879))
        small_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='small_graph_edges', driver='GPKG')
        # graphs with  15–500 edges
        medium_graph_edges_gdf = gpd.GeoDataFrame(medium_graph_edges, crs=CRS.from_epsg(3879))
        medium_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='medium_graph_edges', driver='GPKG')
        # graphs with > 500 edges
        big_graph_edges_gdf = gpd.GeoDataFrame(big_graph_edges, crs=CRS.from_epsg(3879))
        big_graph_edges_gdf.to_file(debug_igraph_gpkg, layer='big_graph_edges', driver='GPKG')
        log.info(f'graphs exported')

    # 10) delete smallest subgraphs from the graph
    del_edge_ids = [edge[Edge.id_ig.name] for edge in small_graph_edges]
    log.info(f'deleting {len(del_edge_ids)} isolated edges')
    before_count = G.ecount()
    G.delete_edges(del_edge_ids)
    after_count = G.ecount()
    del_ratio = round(100 * (before_count-after_count) / before_count, 1)
    log.info(f'deleted {before_count-after_count} ({del_ratio} %) edges')

    # 11) delete isolated nodes from the graph
    del_node_ids = [v.index for v in G.vs.select(_degree_eq=0)]
    log.info(f'deleting {len(del_node_ids)} isolated nodes')
    before_count = G.vcount()
    G.delete_vertices(del_node_ids)
    after_count = G.vcount()
    del_ratio = round(100 * (before_count-after_count) / before_count, 1)
    log.info(f'deleted {before_count-after_count} ({del_ratio} %) nodes')

    # check if id_ig:s need to be updated to edge attributes
    mismatch_count = len([edge.index for edge in G.es if edge.attributes()[Edge.id_ig.value] != edge.index])
    log.info(f'invalid edge ids: {mismatch_count}')
    # reassign igraph indexes to edge and node attributes
    G.es[Edge.id_ig.value] = [e.index for e in G.es]
    G.vs[Node.id_ig.value] = [v.index for v in G.vs]
    # check if id_ig:s need to be updated to edge attributes
    mismatch_count = len([edge.index for edge in G.es if edge.attributes()[Edge.id_ig.value] != edge.index])
    log.info(f'invalid edge ids: {mismatch_count} (after re-indexing)')

    # 12) export graph data to GeoDataFrames fro debugging

    if b_export_final_graph_to_gpkg:
        log.info(f'exporting final graph to {debug_igraph_gpkg} for debugging')
        e_gdf = ig_utils.get_edge_gdf(G, attrs=[Edge.id_otp, Edge.id_ig], ig_attrs=['source', 'target'])
        n_gdf = ig_utils.get_node_gdf(G, ig_attrs=['index'])
        e_gdf.to_file(debug_igraph_gpkg, layer='final_graph_edges', driver='GPKG')
        n_gdf.to_file(debug_igraph_gpkg, layer='final_graph_nodes', driver='GPKG')

    if igraph_out_file:
        ig_utils.export_to_graphml(G, igraph_out_file)

    return G


def main(conf: OtpGraphImportConf):
    graph = convert_otp_graph_to_igraph(
        node_csv_file = conf.node_csv_file,
        edge_csv_file = conf.edge_csv_file,
        hma_poly_file = conf.hma_poly_file,
        igraph_out_file = conf.igraph_out_file,
        b_export_otp_data_to_gpkg = conf.b_export_otp_data_to_gpkg,
        b_export_decomposed_igraphs_to_gpkg = conf.b_export_decomposed_igraphs_to_gpkg,
        b_export_final_graph_to_gpkg = conf.b_export_final_graph_to_gpkg,
        debug_otp_graph_gpkg = conf.debug_otp_graph_gpkg,
        debug_igraph_gpkg = conf.debug_igraph_gpkg,
    )
    log.info(f'created igraph of {graph.ecount()} edges and {graph.vcount()} nodes from OTP data')
