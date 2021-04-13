from collections import Counter
from gp_server.app.types import Bikeability
import gp_server.app.edge_cost_factory_bike as bike_costs
from common.igraph import Edge as E
import geopandas as gpd
import pytest
import graph_build.graph_export.main as graph_export
import common.igraph as ig_utils


graph_name = r'kumpula'
base_dir = r'graph_build/tests/graph_export/'
hel_extent = gpd.read_file(fr'graph_build/tests/common/hel.geojson')


@pytest.fixture()
def graph_in():
    yield ig_utils.read_graphml(fr'{base_dir}graph_in/{graph_name}.graphml')


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


def test_graph_has_allows_biking_attr(graph):
    values = tuple(graph.es[E.allows_biking.value])
    assert len(values) == 16643
    for value in values:
        assert isinstance(value, bool)
    assert values.count(True) == 10715
    assert values.count(False) == 5928


def test_graph_has_is_stairs_attr(graph):
    values = tuple(graph.es[E.is_stairs.value])
    assert len(values) == 16643
    for value in values:
        assert isinstance(value, bool)
    assert values.count(True) == 254
    assert values.count(False) == 16389


def test_graph_has_bike_safety_factor(graph):
    values = tuple(graph.es[E.bike_safety_factor.value])
    assert len(values) == 16643
    for value in values:
        assert isinstance(value, float)
        assert value > 0
        assert value < 10


def test_parses_bikeabilities_as_expected(graph):
    expected_bikeabilities = {
        Bikeability.BIKE_OK: 10715,
        Bikeability.NO_BIKE: 5674,
        Bikeability.NO_BIKE_STAIRS: 254
    }
    bikeabilities = dict(Counter(bike_costs.get_bikeabilities(graph)))
    assert bikeabilities == expected_bikeabilities


def test_length_attributes(graph):
    for length in list(graph.es[E.length.value]):
        assert isinstance(length, float)

    lengths = list(graph.es[E.length.value])

    assert 16643 == len([l for l in lengths if l is not None])
    assert 24.1 == round(sum(lengths) / len(lengths), 1)
