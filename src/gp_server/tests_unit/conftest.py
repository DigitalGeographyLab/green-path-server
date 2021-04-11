from typing import Callable
from gp_server.app.logger import Logger
import gp_server.conf as conf
import gp_server.app.routing as routing
from gp_server.app.graph_handler import GraphHandler
from unittest.mock import patch
import pytest


__noise_sensitivities = [0.1, 0.4, 1.3, 3.5, 6]
__aq_sensitivities = [5, 15, 30]
__gvi_sensitivities = [2, 4, 8]


@pytest.fixture(scope='session')
def log():
    yield Logger()


@pytest.fixture(scope='session')
def routing_conf():
    patch_noise_sens = patch('gp_server.conf.noise_sensitivities', __noise_sensitivities)
    patch_aq_sens = patch('gp_server.conf.aq_sensitivities', __aq_sensitivities)
    patch_gvi_sens = patch('gp_server.conf.gvi_sensitivities', __gvi_sensitivities)
    with patch_noise_sens, patch_aq_sens, patch_gvi_sens:
        yield routing.get_routing_conf()


@pytest.fixture(scope='session')
def graph_handler(log):
    patch_env_test_mode = patch('gp_server.conf.test_mode', True)
    patch_env_graph_file = patch('gp_server.conf.graph_file', r'graphs/kumpula.graphml')
    
    patch_noise_sens = patch('gp_server.conf.noise_sensitivities', __noise_sensitivities)
    patch_aq_sens = patch('gp_server.conf.aq_sensitivities', __aq_sensitivities)
    patch_gvi_sens = patch('gp_server.conf.gvi_sensitivities', __gvi_sensitivities)

    with patch_env_test_mode, patch_env_graph_file, patch_noise_sens, patch_aq_sens, patch_gvi_sens:
        yield GraphHandler(log, conf.graph_file, routing.get_routing_conf())


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
