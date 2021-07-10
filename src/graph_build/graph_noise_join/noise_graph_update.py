import logging
import os
import numpy as np
from pyproj import CRS
from shapely.geometry import Polygon, LineString
import common.igraph as ig_utils
from common.igraph import Edge as E
import common.geometry as geom_utils
import igraph as ig
import pandas as pd
import geopandas as gpd


log = logging.getLogger('noise_graph_update')


def noise_graph_update(graph: ig.Graph, noise_csv_dir: str) -> None:
    """Updates attributes noises and noise_source to graph.
    """

    noise_csvs = os.listdir(noise_csv_dir)

    for csv_file in noise_csvs:
        edge_noises = pd.read_csv(noise_csv_dir + csv_file)
        edge_noises[E.noise_source.name] = edge_noises[E.noise_source.name].replace({np.nan: ''})
        log.info(f'updating {len(edge_noises)} edge noises from '+ csv_file)
        for edge in edge_noises.itertuples():
            graph.es[getattr(edge, E.id_ig.name)][E.noises.value] = getattr(edge, E.noises.name)
            graph.es[getattr(edge, E.id_ig.name)][E.noise_source.value] = getattr(edge, E.noise_source.name)


def set_default_and_na_edge_noises(graph: ig.Graph, data_extent: Polygon) -> None:
    """Sets noise attributes of edges to their default values and None outside the extent of the noise data.
    """

    # first set noise attributes of all edges as nodata
    graph.es[E.noises.value] = None
    graph.es[E.noise_source.value] = None

    edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig])
    data_extent_gdf = gpd.GeoDataFrame(data=[{'has_noise_data': 1}], geometry=[data_extent], crs=CRS.from_epsg(3879))
    joined = gpd.sjoin(edge_gdf, data_extent_gdf, how='left', op='within').drop(['index_right'], axis=1)
    edges_within = joined[joined['has_noise_data'] == 1]

    real_edge_count = len([geom for geom in list(edge_gdf['geometry']) if isinstance(geom, LineString)])
    log.info(f'found {real_edge_count - len(edges_within)} edges of {real_edge_count} outside noise data extent')

    # set noise attributes of edges within the data extent to default values (no noise)
    for edge in edges_within.itertuples():
        graph.es[getattr(edge, E.id_ig.name)][E.noises.value] = {}
        graph.es[getattr(edge, E.id_ig.name)][E.noise_source.value] = ''


if __name__ == '__main__':
    in_graph_file = 'data/hma.graphml'
    out_graph_file = 'out_graph/hma.graphml'
    data_extent_file = 'data/HMA.geojson'
    noise_csv_dir = 'out_csv/'

    data_extent: Polygon = geom_utils.project_geom(gpd.read_file(data_extent_file)['geometry'][0])
    graph = ig_utils.read_graphml(in_graph_file, log)

    set_default_and_na_edge_noises(graph, data_extent)

    noise_graph_update(graph, noise_csv_dir)

    ig_utils.export_to_graphml(graph, out_graph_file)
    log.info(f'exported graph of {graph.ecount()} edges')
    log.info('all done')
