from typing import Union
import geopandas as gpd
from geopandas import GeoDataFrame
import logging
from common.igraph import Edge as E, Node as N
import common.igraph as ig_utils
import graph_build.graph_export.utils as utils
import graph_build.common.conf as conf


log = logging.getLogger('graph_export.main')


def get_bike_cost(
    length: Union[float, None], 
    allows_biking: bool, 
    is_stairs: bool,
    safety_factor: Union[float, None]
) -> float:
    """
    Returns biking cost that is proportional to travel time and adjusted with
    biking safety factor (if provided). 
    """
    if not length:
        return 0
    
    if is_stairs:
        return length * conf.bike_walk_time_ratio * 15
    
    if not allows_biking:
        return length * conf.bike_walk_time_ratio

    if safety_factor:
        return length * safety_factor

    return length


def set_biking_costs(graph):
    # biking time costs
    lengths_allows_biking_is_stairs = zip(
        graph.es[E.length.value],
        graph.es[E.allows_biking.value],
        graph.es[E.is_stairs.value]
    )
    graph.es[E.bike_time_cost.value] = [
        round(
            get_bike_cost(
                length, 
                allows_biking, 
                is_stairs,
                None
            ), 1
        )
        for length, allows_biking, is_stairs
        in lengths_allows_biking_is_stairs
    ]

    # biking safety costs
    lengths_allows_biking_is_stairs_safety_factor = zip(
        graph.es[E.length.value],
        graph.es[E.allows_biking.value],
        graph.es[E.is_stairs.value],
        graph.es[E.bike_safety_factor.value]
    )
    graph.es[E.bike_safety_cost.value] = [
        round(
            get_bike_cost(
                length, 
                allows_biking, 
                is_stairs, 
                safety_factor
            ), 1
        )
        for length, allows_biking, is_stairs, safety_factor
        in lengths_allows_biking_is_stairs_safety_factor
    ]


def set_uv(graph, edge_gdf):
    edge_gdf['uv'] = edge_gdf.apply(lambda x: (x['source'], x['target']), axis=1)
    graph.es[E.uv.value] = list(edge_gdf['uv'])


def set_way_ids(graph, edge_gdf):
    edge_gdf['way_id'] = edge_gdf.apply(lambda x: str(round(x['length'], 1))+str(sorted(x['uv'])), axis=1)
    way_ids = list(edge_gdf['way_id'].unique())
    way_ids_d = { way_id: idx for idx, way_id in enumerate(way_ids) }
    edge_gdf['way_id'] = [way_ids_d[way_id] for way_id in edge_gdf['way_id']]
    graph.es[E.id_way.value] = list(edge_gdf['way_id'])


def graph_export(
    base_dir: str,
    graph_name: str,
    hel_extent: GeoDataFrame
):
    in_graph = fr'{base_dir}graph_in/{graph_name}.graphml'

    out_graph = fr'{base_dir}graph_out/{graph_name}.graphml'
    out_graph_research = fr'{base_dir}graph_out/{graph_name}_r.graphml'
    out_graph_research_hel = fr'{base_dir}graph_out/{graph_name}_r_hel-clip.graphml'
    out_geojson_noise_gvi = fr'{base_dir}graph_out/{graph_name}_noise_gvi.geojson'
    out_geojson = fr'{base_dir}graph_out/{graph_name}.geojson'

    out_node_attrs = [N.geometry]
    out_edge_attrs = [
        E.id_ig, E.uv, E.id_way, E.geometry, E.geom_wgs, 
        E.length, E.bike_time_cost, E.bike_safety_cost, E.noises, E.gvi
    ]

    log.info(f'Reading graph file: {in_graph}')
    graph = ig_utils.read_graphml(in_graph)

    edge_gdf = ig_utils.get_edge_gdf(
        graph, 
        attrs=[E.id_ig, E.length, E.bike_safety_factor], 
        ig_attrs=['source', 'target']
    )

    set_biking_costs(graph)
    set_uv(graph, edge_gdf)
    set_way_ids(graph, edge_gdf)

    # set combined GVI to GVI attribute & export graph
    graph.es[E.gvi.value] = list(graph.es[E.gvi_comb_gsv_veg.value])
    ig_utils.export_to_graphml(graph, out_graph, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)

    # create GeoJSON files for vector tiles
    geojson = utils.create_geojson(graph)
    utils.write_geojson(geojson, out_geojson, overwrite=True, id_attr=True)
    utils.write_geojson(geojson, out_geojson_noise_gvi, overwrite=True, db_prop=True, gvi_prop=True)

    # for research use, set combined GVI that omits low vegetation to GVI attribute and export graph
    graph.es[E.gvi.value] = list(graph.es[E.gvi_comb_gsv_high_veg.value])
    ig_utils.export_to_graphml(graph, out_graph_research, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)

    # export clip of the graph by the extent of Helsinki

    node_gdf = ig_utils.get_node_gdf(graph, attrs=[N.id_ig])
    # replace geometry with buffered one (500 m)
    hel_extent['geometry'] = [geom.buffer(500) for geom in hel_extent['geometry']]
    inside_hel = gpd.sjoin(node_gdf, hel_extent)
    inside_hel_ids = list(inside_hel[N.id_ig.name])
    outside_hel_ids = [id_ig for id_ig in list(node_gdf[N.id_ig.name]) if id_ig not in inside_hel_ids]

    graph.delete_vertices(outside_hel_ids)
    # delete isolated nodes
    del_node_ids = [v.index for v in graph.vs.select(_degree_eq=0)]
    graph.delete_vertices(del_node_ids)
    # reassign igraph indexes to edge and node attributes
    graph.es[E.id_ig.value] = [e.index for e in graph.es]
    graph.vs[N.id_ig.value] = [v.index for v in graph.vs]
    # recalculate uv_id edge attributes
    edge_gdf = ig_utils.get_edge_gdf(
        graph, 
        ig_attrs=['source', 'target']
    )
    set_uv(graph, edge_gdf)

    # export clipped graph
    ig_utils.export_to_graphml(graph, out_graph_research_hel, n_attrs=out_node_attrs, e_attrs=out_edge_attrs)