from typing import Callable
from gp_server.app.logger import Logger
from gp_server.conf import RoutingConf
import gp_server.app.routing as routing
from gp_server.app.graph_handler import GraphHandler
from unittest.mock import patch
import pytest


test_conf = RoutingConf(
    graph_file = r'graphs/kumpula.graphml',
    test_mode = True,
    research_mode = False,
    walk_speed_ms = 1.2,
    bike_speed_ms = 5.55,
    max_od_search_dist_m = 650,
    walking_enabled = True,
    cycling_enabled = True,
    quiet_paths_enabled = True,
    clean_paths_enabled = True,
    gvi_paths_enabled = True,
    use_mean_aqi = False,
    mean_aqi_file_name = None,
    edge_data = False,
    noise_sensitivities = [0.1, 0.4, 1.3, 3.5, 6],
    aq_sensitivities = [5, 15, 30],
    gvi_sensitivities = [2, 4, 8]
)


@pytest.fixture(scope='session')
def log():
    yield Logger()


@pytest.fixture(scope='session')
def routing_conf():
    patch_conf = patch('gp_server.conf.conf', test_conf)
    with patch_conf:
        yield routing.get_routing_conf()


@pytest.fixture(scope='session')
def graph_handler(log):
    patch_conf = patch('gp_server.conf.conf', test_conf)
    with patch_conf:
        yield GraphHandler(log, test_conf.graph_file, routing.get_routing_conf())


@pytest.fixture
def ensure_path_fc() -> Callable[[dict], None]:
    def test_func(path_fc: dict):
        assert path_fc['type'] == 'FeatureCollection'
        assert len(path_fc['features']) >= 1
    return test_func


@pytest.fixture
def ensure_edge_fc() -> Callable[[dict], None]:
    def test_func(path_fc: dict):
        assert path_fc['type'] == 'FeatureCollection'
        assert len(path_fc['features']) > 3
    return test_func
