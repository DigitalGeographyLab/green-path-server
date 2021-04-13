
from typing import List
from common.igraph import Edge as E
from gp_server.app.types import OdNodeData, RoutingConf
import pytest
from shapely.geometry import Point
from gp_server.app.graph_handler import GraphHandler
import gp_server.app.od_handler as od_handler
import common.geometry as geom_utils
import gp_server.app.noise_exposures as noise_exps


@pytest.fixture(scope='module')
def new_nearest_node(graph_handler: GraphHandler) -> OdNodeData:
    point = geom_utils.project_geom(Point(24.97086446863051, 60.21352729760156))
    yield od_handler.get_nearest_node(
        graph_handler,
        point,
        avoid_node_creation = False
    )


@pytest.fixture(scope='module')
def new_linking_edge_data(
    new_nearest_node: OdNodeData,
) -> List[dict]:
    yield od_handler.get_link_edge_data(
        new_nearest_node.id,
        new_nearest_node.link_to_edge_spec,
        create_outbound_links = True,
        create_inbound_links = False
    )


def test_creates_new_nearest_node(new_nearest_node: OdNodeData):
    assert new_nearest_node.is_temp_node
    assert isinstance(new_nearest_node.link_to_edge_spec.edge, dict)
    assert isinstance(new_nearest_node.link_to_edge_spec.snap_point, Point)
    assert new_nearest_node.id == 5956


def test_data_for_linking_edges_has_all_attributes(
    new_nearest_node: OdNodeData,
    new_linking_edge_data: List[dict],
):
    assert len(new_linking_edge_data) == 2
    link_edge = new_linking_edge_data[0]
    assert len(new_nearest_node.link_to_edge_spec.edge) == 28
    for key in new_nearest_node.link_to_edge_spec.edge.keys():
        if key not in [E.id_ig.value, E.id_way.value]:
            assert key in link_edge


def test_data_for_linking_edges_has_right_values(
    new_nearest_node: OdNodeData,
    new_linking_edge_data: List[dict],
):
    assert len(new_linking_edge_data) == 2
    link_edge = new_linking_edge_data[0]
    assert len(new_nearest_node.link_to_edge_spec.edge) == 28

    edge = new_nearest_node.link_to_edge_spec.edge
    link_edge_len_ratio = link_edge[E.length.value] / edge[E.length.value]
    assert round(link_edge_len_ratio, 2) == 0.1
    assert link_edge[E.length.value] == round(link_edge[E.geometry.value].length, 2)
    assert round(geom_utils.project_geom(link_edge[E.geom_wgs.value]).length, 2) == link_edge[E.length.value]
    assert link_edge[E.length.value] == round(link_edge_len_ratio * edge[E.length.value], 2)
    assert link_edge[E.bike_time_cost.value] == round(link_edge_len_ratio * edge[E.bike_time_cost.value], 2)
    assert link_edge[E.bike_safety_cost.value] == round(link_edge_len_ratio * edge[E.bike_safety_cost.value], 2)
    link_edge_total_noise_exp = sum(link_edge[E.noises.value].values())
    assert round(link_edge_total_noise_exp, 2) == link_edge[E.length.value] 
    for key in new_nearest_node.link_to_edge_spec.edge.keys():
        if key.startswith('c_') and not key.startswith('c_aq'):
            assert round(link_edge[key]) == round(link_edge_len_ratio * edge[key])
