import pytest
import gp_server.conf as conf
from shapely.geometry import LineString
from common.igraph import Edge as E
from collections import Counter
import gp_server.app.greenery_exposures as gvi_exps
import gp_server.app.noise_exposures as noise_exps
import gp_server.app.edge_cost_factory_bike as bike_costs
from gp_server.app.logger import Logger
from gp_server.app.graph_handler import GraphHandler
from gp_server.app.graph_aqi_updater import GraphAqiUpdater
from gp_server.app.constants import cost_prefix_dict, TravelMode, RoutingMode
from unittest.mock import patch
from gp_server.app.types import Bikeability
import gp_server.app.routing as routing


__noise_sensitivities = [ 0.1, 0.4, 1.3, 3.5, 6 ]
__aq_sensitivities = [ 5, 15, 30 ]
__gvi_sensitivities = [ 2, 4, 8 ]


@pytest.fixture(scope='module')
def log():
    yield Logger(b_printing=False)


@pytest.fixture(scope='module')
def routing_conf():
    patch_noise_sens = patch('gp_server.app.noise_exposures.get_noise_sensitivities', return_value=__noise_sensitivities)
    patch_aq_sens = patch('gp_server.app.aq_exposures.get_aq_sensitivities', return_value=__aq_sensitivities)
    patch_gvi_sens = patch('gp_server.app.greenery_exposures.get_gvi_sensitivities', return_value=__gvi_sensitivities)
    with patch_noise_sens, patch_aq_sens, patch_gvi_sens:
        yield routing.get_routing_conf()


@pytest.fixture(scope='module')
def graph_handler(log, routing_conf):
    patch_env_test_mode = patch('gp_server.conf.test_mode', True)
    patch_env_graph_file = patch('gp_server.conf.graph_file', r'graphs/kumpula.graphml')
    with patch_env_test_mode, patch_env_graph_file:
        yield GraphHandler(log, conf.graph_file, routing_conf)


@pytest.fixture(scope='module')
def aqi_updater(log, graph_handler, routing_conf):
    patch_env_test_mode = patch('gp_server.conf.test_mode', True)
    with patch_env_test_mode:
        return GraphAqiUpdater(log, graph_handler, r'aqi_updates/test_data/', routing_conf)


def test_initial_aqi_updater_status(aqi_updater):
    aqi_status = aqi_updater.get_aqi_update_status_response()
    assert aqi_status['aqi_data_updated'] == False
    assert aqi_status['aqi_data_utc_time_secs'] == None


def test_updates_aqi_values_to_graph(aqi_updater, graph_handler):
    # do AQI -> graph update
    aqi_edge_updates_csv = 'aqi_2019-11-08T14.csv'
    aqi_updater._GraphAqiUpdater__read_update_aqi_to_graph(aqi_edge_updates_csv)
    
    # check the updated graph (edge attributes)
    aqi_updates = []
    for e in graph_handler.graph.es:
        aqi_updates.append(e.attributes()[E.aqi.value])
    
    assert len(aqi_updates) == 16643
    aqi_updates_ok = [aqi for aqi in aqi_updates if aqi]
    aqi_updates_none = [aqi for aqi in aqi_updates if not aqi]
    assert len(aqi_updates_ok) == 16469
    assert len(aqi_updates_none) == 174


def test_noise_cost_edge_attributes(graph_handler):
    cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.QUIET]

    for e in graph_handler.graph.es:
        attrs = e.attributes()
        eg_noise_cost = f'{cost_prefix}{noise_exps.get_noise_sensitivities()[1]}'
        assert eg_noise_cost in attrs

        if isinstance(attrs[E.geometry.value], LineString) and isinstance(attrs[E.noises.value], dict):
            assert attrs[eg_noise_cost] >= round(attrs[E.length.value], 2)
        elif attrs[E.noises.value] is None and isinstance(attrs[E.geometry.value], LineString):
            assert attrs[eg_noise_cost] > attrs[E.length.value] * 10
        else:
            assert attrs[eg_noise_cost] == 0.0


def test_bike_time_costs_are_added_to_graph(graph_handler: GraphHandler):
    time_costs = list(graph_handler.graph.es[E.bike_time_cost.value])

    for ct in time_costs:
        assert isinstance(ct, (float, int))

    assert 16469 == len([l for l in time_costs if l > 0])
    assert 71.12 == round(sum(time_costs) / len(time_costs), 2)


def test_bike_safety_costs_are_added_to_graph(graph_handler: GraphHandler):
    safety_costs = list(graph_handler.graph.es[E.bike_safety_cost.value])

    for cs in safety_costs:
        assert isinstance(cs, (float, int))

    assert 16469 == len([l for l in safety_costs if l > 0])
    assert 79.14 == round(sum(safety_costs) / len(safety_costs), 2)


def test_no_redundant_edge_attributes_left_in_the_graph(graph_handler: GraphHandler):
    with pytest.raises(KeyError):
        graph_handler.graph.es[E.bike_safety_factor.value]
    with pytest.raises(KeyError):
        graph_handler.graph.es[E.is_stairs.value]


def test_gvi_cost_edge_attributes(graph_handler):
    cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.GREEN]
    for e in graph_handler.graph.es:
        attrs = e.attributes()
        eg_gvi_cost = f'{cost_prefix}{gvi_exps.get_gvi_sensitivities()[1]}'
        assert eg_gvi_cost in attrs

        if not isinstance(attrs[E.geometry.value], LineString):
            assert attrs[eg_gvi_cost] == 0.0
        else:
            assert attrs[eg_gvi_cost] > 0.0
            assert round(attrs[eg_gvi_cost], 2) >= round(attrs[E.length.value], 2)
