from gp_server.conf import RoutingConf
from typing import Dict, Union, Callable
from unittest.mock import patch
import pytest
import json
import time
from common.geometry import project_geom
from shapely.geometry import LineString


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


@pytest.fixture(scope='module')
def initial_client():
    patch_conf = patch('gp_server.conf.conf', test_conf)
    with patch_conf:
        from gp_server_main import app
        with app.test_client() as gp_client:
            yield gp_client


@pytest.fixture(scope='module')
def client(initial_client):
    """Returns API client only when it has loaded AQI data to the routing graph and for AQI map data API."""
    for _ in range(20):
        response = initial_client.get('/aqistatus')
        assert response.status_code == 200
        data = json.loads(response.data)
        if not data.get('aqi_data_updated', None):
            time.sleep(1)
            continue
        response = initial_client.get('/aqi-map-data-status')
        assert response.status_code == 200
        status = json.loads(response.data)
        if not status.get('aqi_map_data_available', None):
            time.sleep(1)
            continue
        break
    yield initial_client


@pytest.fixture
def test_line_geometry() -> Callable[[dict], None]:
    def test_func(geometry: dict):
        assert geometry['type'] == 'LineString'
        coords = geometry['coordinates']
        assert isinstance(coords, list)
        line = LineString(coords)
        assert isinstance(line, LineString)
        assert line.is_valid
        # test that the length is a positive number
        proj_line = project_geom(line)
        assert isinstance(proj_line.length, (float, int))
        assert proj_line.length >= 0.1
    return test_func


@pytest.fixture
def test_exposure_prop_types() -> Callable[[dict, Union[float, None]], None]:
    def test_func(
        exp_dict: Dict[str, Union[int, float]], 
        expected_sum: Union[float, None] = None
    ):
        assert isinstance(exp_dict, dict)
        for key, val in exp_dict.items():
            num_key = int(key)
            assert isinstance(num_key, int)
            assert isinstance(val, (float, int))
        if expected_sum:
            val_sum = sum(exp_dict.values())
            diff = val_sum - expected_sum
            assert abs(diff) <= 0.015 # consider rounding
    return test_func
