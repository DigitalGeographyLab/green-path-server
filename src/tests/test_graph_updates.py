import pytest
import env
from shapely.geometry import LineString
from utils.igraph import Edge as E
import app.greenery_exposures as gvi_exps
import app.noise_exposures as noise_exps
from app.logger import Logger
from app.logger import Logger
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater
from app.constants import cost_prefix_dict, TravelMode, RoutingMode
from unittest.mock import patch


@pytest.fixture(scope='module')
def log():
    yield Logger(b_printing=False)


@pytest.fixture(scope='module')
def graph_handler(log):
    patch_env_test_mode = patch('env.test_mode', True)
    patch_env_graph_file = patch('env.graph_file', r'graphs/kumpula.graphml')
    with patch_env_test_mode, patch_env_graph_file:
        yield GraphHandler(log, env.graph_file)


@pytest.fixture(scope='module')
def aqi_updater(graph_handler, log):
    patch_env_test_mode = patch('env.test_mode', True)
    with patch_env_test_mode:
        return GraphAqiUpdater(log, graph_handler)


def test_initial_aqi_updater_status(aqi_updater):
    aqi_status = aqi_updater.get_aqi_update_status_response()
    assert aqi_status['aqi_data_updated'] == False
    assert aqi_status['aqi_data_utc_time_secs'] == None


def test_aqi_graph_update(aqi_updater, graph_handler):
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

    # aqi updater status response
    aqi_status = aqi_updater.get_aqi_update_status_response()
    assert aqi_status['aqi_data_updated'] == True
    assert aqi_status['aqi_data_utc_time_secs'] > 1000000000


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
            assert round(attrs[eg_gvi_cost], 2) <= round(attrs[E.length.value], 2)
