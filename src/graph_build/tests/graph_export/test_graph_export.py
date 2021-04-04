import geopandas as gpd
import pytest
import graph_build.graph_export.main as graph_export
import common.igraph as ig_utils
from common.igraph import Edge as E


graph_name = r'kumpula'
base_dir = r'graph_build/tests/graph_export/'
hel_extent = gpd.read_file(fr'graph_build/tests/common/hel.geojson')


@pytest.fixture(scope='session')
def graph():
    graph_export.graph_export(
        base_dir,
        graph_name,
        hel_extent
    )
    yield ig_utils.read_graphml(fr'{base_dir}graph_out/{graph_name}.graphml')


def test_feature_counts(graph):
    assert graph.ecount() == 16643
    assert graph.vcount() == 5956


def test_length_attributes(graph):
    for length in list(graph.es[E.length.value]):
        assert isinstance(length, float)
