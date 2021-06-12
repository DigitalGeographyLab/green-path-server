from gp_server.conf import RoutingConf
from unittest.mock import patch
import pytest


test_conf = RoutingConf(
    graph_file = r'graphs/kumpula.graphml',
    test_mode = True,
    research_mode = True,
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
    edge_data = True,
    noise_sensitivities = [0.1, 0.4, 1.3, 3.5, 6],
    aq_sensitivities = [5, 15, 30],
    gvi_sensitivities = [2, 4, 8]
)


@pytest.fixture(scope='module')
def client():
    patch_conf = patch('gp_server.conf.conf', test_conf)
    with patch_conf:
        from gp_server_main import app
        with app.test_client() as gp_client:
            yield gp_client
