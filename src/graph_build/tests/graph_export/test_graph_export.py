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

    lengths = list(graph.es[E.length.value])

    assert 16643 == len([l for l in lengths if l is not None])
    assert 24.1 == round(sum(lengths) / len(lengths), 1)


def test_bike_time_costs(graph):
    time_costs = list(graph.es[E.bike_time_cost.value])

    for ct in time_costs:
        assert isinstance(ct, float)

    assert 16469 == len([l for l in time_costs if l > 0])
    assert 61.83 == round(sum(time_costs) / len(time_costs), 2)


def test_bike_safety_costs(graph):
    safety_costs = list(graph.es[E.bike_safety_cost.value])

    for cs in safety_costs:
        assert isinstance(cs, float)

    assert 16469 == len([l for l in safety_costs if l > 0])
    assert 69.86 == round(sum(safety_costs) / len(safety_costs), 2)
