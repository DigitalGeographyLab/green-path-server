import os
from collections import Counter
import pytest
import fiona
import numpy as np
import pandas as pd
import geopandas as gpd
import graph_build.graph_noise_join.utils as utils
import common.igraph as ig_utils
from graph_build.graph_noise_join import noise_graph_join, noise_graph_update
from common.igraph import Edge as E
import common.geometry as geom_utils
from shapely.geometry import LineString, Polygon, Point


base_dir = r'graph_build/tests/graph_noise_join'


def test_calculates_point_sampling_distances():
    sampling_points = utils.get_point_sampling_distances(5)
    assert len(sampling_points) == 5
    assert sampling_points[0] == (1/5)/2
    assert sampling_points[1] == (1/5)/2 + 1/5
    assert sampling_points[4] == (1/5)/2 + 4 * (1/5)
    sampling_points = utils.get_point_sampling_distances(1)
    assert sampling_points[0] == 0.5


def test_adds_sampling_points_to_edge_gdf():
    graph = ig_utils.read_graphml(f'{base_dir}/data/test_graph.graphml')
    gdf = ig_utils.get_edge_gdf(graph)
    # start_time = time.time()
    gdf = utils.add_sampling_points_to_gdf(gdf, 2)
    # log.duration(start_time, 'added sampling points')
    sampling_points_list = list(gdf['sampling_points'])
    assert len([sps for sps in sampling_points_list if sps != None]) == 3522
    assert len([sps for sps in sampling_points_list if sps == None]) == 180
    # test that all sample points are on the line geometries
    for edge in gdf.itertuples():
        sampling_points = getattr(edge, 'sampling_points')
        if (sampling_points == None): continue
        line_geom = getattr(edge, 'geometry')
        for sp in sampling_points:
            assert round(sp.distance(line_geom), 1) == 0, 5

    # validate sampling point gdf (exploaded from edge gdf with sampling points)
    sampling_gdf = utils.explode_sampling_point_gdf(gdf, 'sampling_points')
    assert len(sampling_gdf) > len(gdf)
    assert len(sampling_gdf) == 58554
    # check that the total representative length of each set of sampling points equals the length of the respective edge
    sps_by_edge = sampling_gdf.groupby('edge_id')
    for edge in gdf.itertuples():
        if (edge.sampling_points != None):
            edge_sps = sps_by_edge.get_group(edge.Index)
            sampling_length_sum = edge_sps['sample_len'].sum()
            assert round(sampling_length_sum, 2) == round(edge.geometry.length, 2)


def test_creates_distributed_sampling_points_around_point():
    point = Point(25501668.9, 6684943.1)
    sps = utils.get_sampling_points_around(point, 40, count=20)
    assert len(sps) == 20
    for sp in sps:
        assert round(sp.distance(point), 1) == 40
    distances_between = [sp.distance(point) for point in sps]
    assert round(np.std(distances_between), 3) == 24.812


@pytest.mark.skip(reason="run before and slow")
def test_joins_noises_to_graph_edges():
    graph = ig_utils.read_graphml(f'{base_dir}/data/test_graph.graphml')
    edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.length])
    edge_gdf[E.id_ig.name] = edge_gdf.index
    # read noise data
    noise_layer_names = [layer for layer in fiona.listlayers(f'{base_dir}/data/noise_data_processed.gpkg')]
    noise_layers = {name: gpd.read_file(f'{base_dir}/data/noise_data_processed.gpkg', layer=name) for name in noise_layer_names}
    noise_layers = {name: gdf.rename(columns={'db_low': name}) for name, gdf in noise_layers.items()}

    # read nodata zone: narrow area between noise surfaces of different municipalities
    nodata_layer = gpd.read_file(f'{base_dir}/data/extents.gpkg', layer='municipal_boundaries')

    edge_noises = noise_graph_join.noise_graph_join(
        edge_gdf=edge_gdf,
        sampling_interval=3,
        noise_layers=noise_layers,
        nodata_layer=nodata_layer
    )

    assert edge_noises[E.id_ig.name].nunique() == 3522

    edge_noises_df = pd.merge(edge_gdf, edge_noises, how='inner', on=E.id_ig.name)
    edge_noises_df['total_noise_len'] = [round(sum(noises.values()), 4) for noises in edge_noises_df['noises']]

    def validate_edge_noises(row):
        assert round(row['total_noise_len'], 1) <= round(row['length'], 1)

    edge_noises_df.apply(lambda row: validate_edge_noises(row), axis=1)

    assert round(edge_noises_df['total_noise_len'].mean(), 2) == 33.20

    # test frequency of different main noise sources
    noise_sources = dict(Counter(list(edge_noises_df[E.noise_source.name])))
    assert noise_sources == {'road': 2322, 'train': 1198, '': 2}


@pytest.fixture
def rm_temp_graph_file():
    yield
    os.remove(f'{base_dir}/temp/test_graph_noises.graphml')


@pytest.mark.usefixtures('rm_temp_graph_file')
def test_updates_noises_from_csv_to_graph():
    in_graph_file = f'{base_dir}/data/test_graph.graphml'
    out_graph_file = f'{base_dir}/temp/test_graph_noises.graphml'
    data_extent_file = f'{base_dir}/data/HMA.geojson'
    noise_csv_dir = f'{base_dir}/noise_csv/'

    data_extent: Polygon = geom_utils.project_geom(gpd.read_file(data_extent_file)['geometry'][0])
    graph = ig_utils.read_graphml(in_graph_file)

    noise_graph_update.set_default_and_na_edge_noises(graph, data_extent)

    noise_graph_update.noise_graph_update(graph, noise_csv_dir)
    ig_utils.export_to_graphml(graph, out_graph_file)

    graph = ig_utils.read_graphml(out_graph_file)

    assert graph.ecount() == 3702

    for edge in graph.es:
        attrs = edge.attributes()

        # check that edge IDs are correct
        assert edge.index == attrs[E.id_ig.value]

        if isinstance(attrs[E.geometry.value], LineString):
            # note: this will fail if some of the edges are outside the noise data extent
            assert edge[E.noises.value] is not None
            assert isinstance(edge[E.noises.value], dict)
            assert edge[E.noise_source.value] is not None
            assert isinstance(edge[E.noise_source.value], str)
        else:
            # for edges without geometry the noise attributes should be nodata
            assert edge[E.noises.value] is None
            assert edge[E.noise_source.value] is None

        # if edge noises are nodata then also noise source must be nodata
        if edge[E.noises.value] is None:
            assert edge[E.noise_source.value] is None

        # if edge noises are not nodata but {} then noise source must also be just '' (not nodata)
        if edge[E.noises.value] == {}:
            assert edge[E.noise_source.value] == ''

        # if edge has noises it must also have noise source
        if edge[E.noises.value]:
            assert edge[E.noise_source.value] != ''
            assert edge[E.noise_source.value] is not None

        # if edge has noise source it must have also noises
        if edge[E.noise_source.value]:
            assert edge[E.noises.value] != ''
            assert edge[E.noises.value] is not None
